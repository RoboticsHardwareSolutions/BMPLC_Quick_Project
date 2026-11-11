"""Host test of usb_bridge, CAN target in App mode (../target/usb_bridge_echo.c, `usb_bridge_echo can`).

No CAN bus, no HIL stand: the board over USB plus the J-Link for RTT, see usb_bridge_hw.py. The echo application:

    data frame id          -> same frame with id + 1
    RTR frame id, DLC n    -> data frame id + 1, DLC n, payload 0, 1, .. n-1
    std 0x7FF [01 hi lo]   -> burst of (hi << 8 | lo) std frames 0x100 with a 16-bit big endian sequence number
    std 0x7FF [02] / [03]  -> start / stop a periodic sender of std frames 0x101 every 10 ms

    USB_BRIDGE_PORT=/dev/cu.usbmodem21201 JLINK_SERIAL=772440188 MCU=STM32G0B1KC \
        uv run pytest user_tests/usb_bridge_test/testbench/ -v
"""

from __future__ import annotations

import time
from typing import Iterator

import pytest

import usb_bridge_hw as hw

can = pytest.importorskip("can")
serial = pytest.importorskip("serial")

BITRATE = 500000
RX_TIMEOUT_S = 1.0

CONTROL_ID = 0x7FF
BURST_ID = 0x100

pytestmark = hw.requires_hw


@pytest.fixture(scope="module", autouse=True)
def echo_can(plc) -> Iterator[None]:
    hw.echo_start(plc, "can")
    yield
    hw.echo_stop(plc)


# ------------------------------------------------------------------ raw SLCAN


class RawSlcan:
    """Line level access for the protocol checks python-can hides (OK/BELL answers)."""

    def __init__(self, port: str) -> None:
        self.ser = serial.Serial(port, 115200, timeout=0.05)
        self.ser.reset_input_buffer()

    def close(self) -> None:
        self.ser.close()

    def read_answer(self, timeout: float = RX_TIMEOUT_S) -> str:
        """Next answer up to and including its CR or BELL."""
        buf = bytearray()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            b = self.ser.read(1)
            if not b:
                continue
            buf += b
            if b in (b"\r", b"\a"):
                return buf.decode()
        raise TimeoutError(f"no answer, got {bytes(buf)!r}")

    def cmd(self, line: str) -> str:
        self.ser.write(line.encode() + b"\r")
        return self.read_answer()

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


@pytest.fixture
def raw() -> Iterator[RawSlcan]:
    r = RawSlcan(hw.PORT)
    r.cmd("C")
    r.drain()
    try:
        yield r
    finally:
        r.cmd("C")
        r.close()


# ------------------------------------------------------------------ python-can


@pytest.fixture
def bus() -> Iterator[can.BusABC]:
    b = can.Bus(interface="slcan", channel=hw.PORT, bitrate=BITRATE, sleep_after_open=0.2)
    try:
        _flush(b)
        yield b
    finally:
        b.shutdown()


def _flush(b: can.BusABC) -> None:
    while b.recv(0.1) is not None:
        pass


def _recv_frames(b: can.BusABC, count: int, timeout: float) -> list[can.Message]:
    frames = []
    deadline = time.monotonic() + timeout
    while len(frames) < count and time.monotonic() < deadline:
        msg = b.recv(0.1)
        if msg is not None:
            frames.append(msg)
    return frames


def _echo(b: can.BusABC, msg: can.Message) -> can.Message:
    b.send(msg)
    reply = b.recv(RX_TIMEOUT_S)
    assert reply is not None, f"no echo for {msg}"
    return reply


# ------------------------------------------------------------------ 1. protocol


def test_open_close_answers(raw: RawSlcan) -> None:
    assert raw.cmd("S6") == "\r"
    assert raw.cmd("O") == "\r"
    assert raw.cmd("O") == "\a", "second O on an open channel must fail"
    assert raw.cmd("S4") == "\a", "bitrate change on an open channel must fail"
    assert raw.cmd("C") == "\r"
    assert raw.cmd("C") == "\r", "C on a closed channel is accepted"


def test_invalid_commands(raw: RawSlcan) -> None:
    assert raw.cmd("X") == "\a"
    assert raw.cmd("S9") == "\a"
    assert raw.cmd("L") == "\a", "listen-only is not supported"
    assert raw.cmd("Z1") == "\a", "timestamps are not supported"
    assert raw.cmd("Z0") == "\r"
    assert raw.cmd("t1230") == "\a", "transmit on a closed channel must fail"
    assert raw.cmd("O") == "\r"
    assert raw.cmd("t800") == "\a", "std id > 0x7FF"
    assert raw.cmd("t1239") == "\a", "DLC > 8"
    assert raw.cmd("t12321") == "\a", "data shorter than DLC"
    assert raw.cmd("x" * 40) == "\a", "line longer than the reader buffer"
    assert raw.cmd("") == "\r", "empty line"


def test_version_and_serial(raw: RawSlcan) -> None:
    assert raw.cmd("V") == "V1010\r"
    assert raw.cmd("v") == "v1010\r"
    serial_answer = raw.cmd("N")
    assert len(serial_answer) == 6 and serial_answer[0] == "N" and serial_answer[-1] == "\r"
    int(serial_answer[1:5], 16)


def test_python_can_version_and_serial(bus: can.BusABC) -> None:
    assert bus.get_version(RX_TIMEOUT_S) == (10, 10)
    assert bus.get_serial_number(RX_TIMEOUT_S) is not None


def test_transmit_ack(raw: RawSlcan) -> None:
    assert raw.cmd("S6") == "\r"
    assert raw.cmd("O") == "\r"
    assert raw.cmd("t1231AA") == "z\r"
    assert raw.read_answer() == "t1241AA\r"
    assert raw.cmd("T000001231BB") == "Z\r"
    assert raw.read_answer() == "T000001241BB\r"


# ------------------------------------------------------------------ 2-4. echo


@pytest.mark.parametrize("can_id", [0x000, 0x123, 0x7FE])
@pytest.mark.parametrize("dlc", range(9))
def test_echo_std(bus: can.BusABC, can_id: int, dlc: int) -> None:
    data = bytes((can_id + i * 17) & 0xFF for i in range(dlc))
    reply = _echo(bus, can.Message(arbitration_id=can_id, data=data, is_extended_id=False))
    assert reply.arbitration_id == can_id + 1
    assert not reply.is_extended_id
    assert not reply.is_remote_frame
    assert reply.dlc == dlc
    assert bytes(reply.data) == data


@pytest.mark.parametrize("can_id", [0x00000000, 0x00000800, 0x12345678, 0x1FFFFFFE])
def test_echo_ext(bus: can.BusABC, can_id: int) -> None:
    data = bytes([0xDE, 0xAD, 0xBE, 0xEF])
    reply = _echo(bus, can.Message(arbitration_id=can_id, data=data, is_extended_id=True))
    assert reply.arbitration_id == can_id + 1
    assert reply.is_extended_id
    assert bytes(reply.data) == data


def test_echo_ext_wraps(bus: can.BusABC) -> None:
    reply = _echo(bus, can.Message(arbitration_id=0x1FFFFFFF, data=b"\x01", is_extended_id=True))
    assert reply.arbitration_id == 0
    assert reply.is_extended_id


@pytest.mark.parametrize("extended", [False, True])
@pytest.mark.parametrize("dlc", [0, 4, 8])
def test_rtr(bus: can.BusABC, extended: bool, dlc: int) -> None:
    reply = _echo(
        bus, can.Message(arbitration_id=0x123, is_remote_frame=True, dlc=dlc, is_extended_id=extended)
    )
    assert reply.arbitration_id == 0x124
    assert reply.is_extended_id == extended
    assert not reply.is_remote_frame
    assert reply.dlc == dlc
    assert bytes(reply.data) == bytes(range(dlc))


# ------------------------------------------------------------------ 5-6. throughput


@pytest.mark.parametrize("count", [1, 200, 1000])
def test_app_burst(bus: can.BusABC, count: int) -> None:
    """App-initiated stream to the host: in order, nothing lost (CDC TX backpressure)."""
    bus.send(can.Message(arbitration_id=CONTROL_ID, data=[0x01, count >> 8, count & 0xFF], is_extended_id=False))
    frames = _recv_frames(bus, count, timeout=5.0 + count / 100)
    assert len(frames) == count, f"got {len(frames)} of {count}"
    for seq, msg in enumerate(frames):
        assert msg.arbitration_id == BURST_ID
        assert int.from_bytes(msg.data, "big") == seq
    assert bus.recv(0.3) is None, "more frames than requested"


def test_host_stress(bus: can.BusABC) -> None:
    """1000 frames from the host back to back: every echo arrives, in order."""
    count = 1000
    for i in range(count):
        bus.send(can.Message(arbitration_id=0x200, data=i.to_bytes(2, "big"), is_extended_id=False))
    frames = _recv_frames(bus, count, timeout=20.0)
    assert len(frames) == count, f"got {len(frames)} of {count}"
    for i, msg in enumerate(frames):
        assert msg.arbitration_id == 0x201
        assert int.from_bytes(msg.data, "big") == i


# ------------------------------------------------------------------ 7. closed channel


def _periodic_frames(data: bytes) -> list[int]:
    """Sequence numbers of the periodic sender's t1012xxxx frames in a raw SLCAN stream."""
    return [int(line[5:9], 16) for line in data.decode().split("\r") if line.startswith("t1012")]


def test_no_frames_while_closed(raw: RawSlcan) -> None:
    """Frames the app sends (from its timer thread) reach the host only while the channel is open."""
    assert raw.cmd("O") == "\r"
    raw.ser.write(b"t7FF102\r")  # start the periodic sender
    try:
        time.sleep(0.5)
        seqs = _periodic_frames(raw.drain())
        assert len(seqs) >= 10, "periodic sender is not running"
        assert seqs == list(range(seqs[0], seqs[0] + len(seqs))), "periodic frames lost or reordered"

        raw.ser.write(b"C\r")
        tail = raw.drain()  # frames queued before C, then the OK
        assert tail.endswith(b"\r")
        time.sleep(0.5)
        assert raw.drain() == b"", "frames sent to the host while the channel is closed"

        assert raw.cmd("O") == "\r"
        time.sleep(0.3)
        assert len(_periodic_frames(raw.drain())) >= 5, "frames do not resume after O"
    finally:
        raw.ser.write(b"O\rt7FF103\r")  # stop the periodic sender, the channel must be open for that
        raw.drain()


# ------------------------------------------------------------------ 8. physical CAN untouched


def test_status_no_bus_errors(raw: RawSlcan) -> None:
    """App mode never starts the physical CAN, so F never reports bus errors or overruns."""
    assert raw.cmd("F") == "\a", "F on a closed channel must fail"
    assert raw.cmd("O") == "\r"
    for i in range(20):
        assert raw.cmd(f"t1231{i:02X}") == "z\r"
        assert raw.read_answer() == f"t1241{i:02X}\r"
    assert raw.cmd("F") == "F00\r"
