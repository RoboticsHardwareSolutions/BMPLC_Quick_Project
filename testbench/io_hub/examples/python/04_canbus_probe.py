#!/usr/bin/env python3
"""Standalone diagnostic utility for the bench's [iface.canbus] adapter (currently a
CANable 2.0, slcan/Lawicel-style ASCII protocol over a USB-CDC virtual COM port) --
talks to it directly, without the PLC/J-Link/pytest fixture chain, so you can poke at
the adapter itself while debugging "no CAN traffic arrives" style problems.

Port resolution: by default, asks a running testbench daemon via
TestbenchClient.iface_available(TB_IFACE_CANBUS) for the adapter's current /dev path
(same mechanism user_tests/usb_bridge_test uses) -- pass --port to talk to an explicit
path instead (e.g. if no daemon is running, or you want to point this at the PLC's own
CDC SLCAN port for comparison).

Prerequisites:
    - a testbench daemon must already be running (unless --port is given), e.g. from
      testbench/io_hub/:  ./build/testbench --config ../testbench.toml
    - `pyserial`, a core dependency of the repo-root pyproject.toml:  uv sync

Usage (from the repo root):
    uv run python testbench/io_hub/examples/python/04_canbus_probe.py status
    uv run python testbench/io_hub/examples/python/04_canbus_probe.py send 123 01020304
    uv run python testbench/io_hub/examples/python/04_canbus_probe.py send 123 01020304 --ext
    uv run python testbench/io_hub/examples/python/04_canbus_probe.py listen 10
    uv run python testbench/io_hub/examples/python/04_canbus_probe.py repl
    uv run python testbench/io_hub/examples/python/04_canbus_probe.py status --port /dev/cu.usbmodem312301

SLCAN quick reference (what `repl` lets you type raw):
    Sxx\\r   set bitrate (S4=125k S5=250k S6=500k S8=1M)       -> \\r ok, \\a error
    O\\r      open channel                                     -> \\r ok, \\a error
    C\\r      close channel                                    -> \\r ok, \\a error
    tIIILDD..\\r  send std data frame (III=3 hex id, L=1 hex len, DD=hex bytes) -> z\\r ack
    RIIIIIIIILDD..\\r  send ext data frame (IIIIIIII=8 hex id)  -> Z\\r ack
    F\\r      read+clear status flags (bitfield, see decode_status_flags below)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import serial

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "client" / "python"))

from testbench_client import TB_IFACE_CANBUS, TestbenchClient  # noqa: E402

_BITRATE_CODE = {10000: "0", 20000: "1", 50000: "2", 100000: "3", 125000: "4", 250000: "5", 500000: "6", 750000: "7", 1000000: "8"}

_STATUS_FLAGS = {
    0: "RX FIFO full",
    1: "TX FIFO full",
    2: "error warning",
    3: "data overrun",
    5: "error passive",
    6: "arbitration lost",
    7: "bus error",
}


def resolve_port(explicit: str | None) -> str:
    if explicit:
        return explicit
    with TestbenchClient() as client:
        if not client.ping():
            print("testbench daemon not reachable -- pass --port explicitly instead", file=sys.stderr)
            raise SystemExit(1)
        present, path = client.iface_available(TB_IFACE_CANBUS)
        if not present:
            print("[iface.canbus] not currently detected by the daemon -- pass --port explicitly instead", file=sys.stderr)
            raise SystemExit(1)
        return path


#: The bench's current [iface.canbus] adapter (CANable 2.0) is a plain USB-CDC device, same as the PLC's
#: own CDC port -- the tty baud is cosmetic, 115200 is just the conventional default. (A prior bench adapter,
#: a VScom USB-CAN Plus, needed a real, non-cosmetic 3,000,000 baud per its own FTDI-backed UART datasheet --
#: if that adapter is ever reconnected, pass --tty-baud 3000000 explicitly.)
CANBUS_TTY_BAUD = 115200


class RawSlcan:
    """Line-level SLCAN access -- no python-can abstraction, so you see exactly what
    the adapter answers (\\r = ok, \\a = BEL = error) for each raw command."""

    def __init__(self, port: str, tty_baud: int = CANBUS_TTY_BAUD, read_timeout: float = 0.5) -> None:
        self.ser = serial.Serial(port, tty_baud, timeout=read_timeout)
        self.ser.reset_input_buffer()

    def close(self) -> None:
        self.ser.close()

    def __enter__(self) -> "RawSlcan":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def cmd(self, line: str, timeout: float = 1.0, settle: float = 0.15) -> str:
        """Send one SLCAN command, wait `settle` seconds, then return everything that
        arrived (raises TimeoutError if nothing arrived at all -- the adapter isn't
        answering, as opposed to answering with an error).

        Deliberately waits-then-reads-everything rather than reading byte-by-byte and
        stopping at the first CR/BEL: some commands (e.g. this adapter's `N`, likely
        an EEPROM read) answer in two separate chunks with a gap between them, which
        a stop-on-first-terminator reader misattributes to the wrong command."""
        self.ser.write(line.encode() + b"\r")
        buf = bytearray()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(settle)
            chunk = self.ser.read(self.ser.in_waiting or 1)
            if not chunk:
                if buf:
                    return buf.decode(errors="replace")
                continue
            buf += chunk
        if buf:
            return buf.decode(errors="replace")
        raise TimeoutError(f"no answer to {line!r}")

    def drain(self, quiet: float = 0.2, limit: float = 2.0) -> bytes:
        """Everything received until the line is quiet for `quiet` s, at most `limit` s."""
        data = bytearray()
        end = time.monotonic() + limit
        deadline = time.monotonic() + quiet
        while time.monotonic() < min(deadline, end):
            chunk = self.ser.read(256)
            if chunk:
                data += chunk
                deadline = time.monotonic() + quiet
        return bytes(data)


def decode_status_flags(resp: str) -> str:
    # resp is "F<2 hex digits><CR>" on success
    hexpart = resp.strip("\rF")
    try:
        flags = int(hexpart, 16)
    except ValueError:
        return f"could not parse {resp!r}"
    if flags == 0:
        return "no errors"
    names = [name for bit, name in _STATUS_FLAGS.items() if flags & (1 << bit)]
    return f"0x{flags:02x}: {', '.join(names) if names else 'unknown bits set'}"


def _try_cmd(dev: RawSlcan, label: str, line: str) -> str | None:
    """Run one SLCAN command, print its outcome, and return the response (or None if
    the adapter never answered at all -- reported, not raised, so `status` can keep
    going and show exactly which commands get a response and which don't)."""
    try:
        resp = dev.cmd(line)
        print(f"{label}:", repr(resp))
        return resp
    except TimeoutError:
        print(f"{label}: NO RESPONSE (adapter did not answer at all)")
        return None


def cmd_status(port: str, bitrate: int, tty_baud: int) -> int:
    responded = False
    with RawSlcan(port, tty_baud) as dev:
        if _try_cmd(dev, "close (in case already open)", "C") is not None:
            responded = True
        if _try_cmd(dev, "hw version V", "V") is not None:
            responded = True
        if _try_cmd(dev, "serial N", "N") is not None:
            responded = True
        if not responded:
            sys.stdout.flush()
            print(
                "\nThe adapter did not answer ANY command at the serial-protocol level, even though its USB port "
                "is enumerated. This points to the adapter itself (power-cycle it: unplug/replug), not to CAN bus "
                "wiring/termination -- a wiring/termination problem would still let SLCAN commands succeed, since "
                "those don't touch the physical CAN bus at all.",
                file=sys.stderr,
            )
            return 1
        bitrate_resp = _try_cmd(dev, f"set bitrate S{_BITRATE_CODE[bitrate]} ({bitrate})", f"S{_BITRATE_CODE[bitrate]}")
        open_resp = _try_cmd(dev, "open O", "O")
        if open_resp is not None:
            print(" ->", "OK" if open_resp.endswith("\r") else "ERROR (channel did not open)")
        time.sleep(0.3)
        flags = _try_cmd(dev, "status F", "F")
        if flags is not None:
            print(" ->", decode_status_flags(flags))
        _try_cmd(dev, "close C", "C")
    return 0 if (bitrate_resp and open_resp and open_resp.endswith("\r")) else 1


def cmd_send(port: str, bitrate: int, tty_baud: int, can_id: int, data: bytes, extended: bool) -> int:
    with RawSlcan(port, tty_baud) as dev:
        dev.cmd("C")
        dev.cmd(f"S{_BITRATE_CODE[bitrate]}")
        open_resp = dev.cmd("O")
        if not open_resp.endswith("\r"):
            print("open failed:", repr(open_resp), file=sys.stderr)
            return 1
        if extended:
            line = f"R{can_id:08X}{len(data)}{data.hex().upper()}"
        else:
            line = f"t{can_id:03X}{len(data)}{data.hex().upper()}"
        print("sending:", line)
        resp = dev.cmd(line)
        print("ack:", repr(resp), "-> OK" if resp[:1] in ("z", "Z") else "-> ERROR")
        dev.cmd("C")
    return 0


def cmd_listen(port: str, bitrate: int, tty_baud: int, seconds: float) -> int:
    with RawSlcan(port, tty_baud, read_timeout=0.1) as dev:
        dev.cmd("C")
        dev.cmd(f"S{_BITRATE_CODE[bitrate]}")
        open_resp = dev.cmd("O")
        if not open_resp.endswith("\r"):
            print("open failed:", repr(open_resp), file=sys.stderr)
            return 1
        print(f"listening for {seconds}s (Ctrl+C to stop early)...")
        deadline = time.monotonic() + seconds
        try:
            while time.monotonic() < deadline:
                raw = dev.drain(quiet=0.1, limit=0.5)
                if raw:
                    print(raw.decode(errors="replace"), end="")
        except KeyboardInterrupt:
            pass
        dev.cmd("C")
    return 0


def cmd_repl(port: str, tty_baud: int) -> int:
    print(f"raw SLCAN REPL on {port} @ {tty_baud} baud -- type commands without CR (e.g. S6, O, t1230102, F, C), Ctrl+D to quit")
    with RawSlcan(port, tty_baud) as dev:
        while True:
            try:
                line = input("slcan> ").strip()
            except EOFError:
                print()
                break
            if not line:
                continue
            try:
                print(repr(dev.cmd(line)))
            except TimeoutError as e:
                print(f"(no response: {e})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", help="explicit /dev path; default: resolve [iface.canbus] via the daemon")
    parser.add_argument("--baud", type=int, default=500000, choices=sorted(_BITRATE_CODE), help="CAN bitrate (default 500000)")
    parser.add_argument(
        "--tty-baud",
        type=int,
        default=CANBUS_TTY_BAUD,
        help=f"serial/USB-CDC baud for the adapter's virtual COM port (default {CANBUS_TTY_BAUD}, cosmetic for "
        "USB-CDC adapters like CANable2/the PLC's own port -- pass 3000000 if --port points at a VScom "
        "USB-CAN Plus instead, which needs its real, non-cosmetic rate)",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("status", help="open the channel, print version/serial/status flags, close")

    p_send = sub.add_parser("send", help="open, send one frame, print the ack, close")
    p_send.add_argument("id", help="CAN id, hex (e.g. 123)")
    p_send.add_argument("data", help="payload bytes, hex (e.g. 01020304), may be empty")
    p_send.add_argument("--ext", action="store_true", help="29-bit extended id instead of 11-bit standard")

    p_listen = sub.add_parser("listen", help="open the channel and print raw SLCAN lines received")
    p_listen.add_argument("seconds", type=float, nargs="?", default=10.0)

    sub.add_parser("repl", help="interactive: type raw SLCAN commands, see raw responses")

    args = parser.parse_args()
    port = resolve_port(args.port)
    print(f"using port: {port}")

    if args.action == "status":
        return cmd_status(port, args.baud, args.tty_baud)
    if args.action == "send":
        return cmd_send(port, args.baud, args.tty_baud, int(args.id, 16), bytes.fromhex(args.data), args.ext)
    if args.action == "listen":
        return cmd_listen(port, args.baud, args.tty_baud, args.seconds)
    if args.action == "repl":
        return cmd_repl(port, args.tty_baud)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
