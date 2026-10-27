"""Low-latency Python client for the testbench daemon's NNG IPC API.

Mirrors testbench/io_hub/client/c/testbench_client.h. Label names are resolved locally
from testbench.toml (the same file the daemon reads) -- only bit positions/addresses
ever go over the wire, matching testbench/io_hub/include/testbench_proto.h exactly.

Requires the optional `pynng` dependency (not installed by default -- see
pyproject.toml's `ipc` extra: `uv sync --extra ipc`), since it's only needed by code
that talks to a running daemon over IPC, not by the HIL test suite.
"""

from __future__ import annotations

import struct
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pynng

TB_PROTO_VERSION = 1
TB_IPC_DEFAULT_URL = "ipc:///tmp/testbench.ipc"

_OP_PING = 0
_OP_GET_INPUTS = 1
_OP_GET_OUTPUTS = 2
_OP_SET_COILS_MASK = 3
_OP_GET_STATUS = 4
_OP_GET_IFACE_STATUS = 5

_STATUS_OK = 0

# The four well-known [iface.*] interface kinds iface_available() can ask about --
# mirrors the TB_IFACE_* enum in testbench_proto.h exactly.
TB_IFACE_CANBUS = 0
TB_IFACE_RS422 = 1
TB_IFACE_RS485 = 2
TB_IFACE_RS232 = 3

# "=" -- native byte order, standard size, NO padding: matches the daemon's
# #pragma pack(push, 1) C structs (testbench_proto.h) exactly.
_REQ_HEADER = struct.Struct("=BB")
_RESP_HEADER = struct.Struct("=BB")
_SET_COILS_REQ = struct.Struct("=II")
_INPUTS_RESP = struct.Struct("=IQB")
_OUTPUTS_RESP = struct.Struct("=Iii")
_STATUS_RESP = struct.Struct("=QQQ")
_IFACE_STATUS_REQ = struct.Struct("=B")
_IFACE_STATUS_RESP = struct.Struct("=B64s")

_RECV_TIMEOUT_MS = 1000
_SEND_TIMEOUT_MS = 1000


class TestbenchIpcError(RuntimeError):
    """Raised when the daemon is unreachable, or returns a non-OK status.

    A non-OK status covers two distinct situations: get_inputs()/get_outputs() raise it
    when the daemon is reachable but the corresponding direction's last Modbus poll
    didn't actually reach the bus (no trustworthy data to hand back), and
    set_coils_mask() raises it when a write would never reach the hardware right now
    (rejected outright rather than silently queued). ping() and get_status() are NOT
    gated on Modbus health -- they stay available so callers can diagnose *why* the
    others are failing."""


class TestbenchClient:
    """One NNG REQ socket dialed to a running testbench daemon."""

    def __init__(self, url: str = TB_IPC_DEFAULT_URL):
        self._sock = pynng.Req0(dial=url, recv_timeout=_RECV_TIMEOUT_MS, send_timeout=_SEND_TIMEOUT_MS)

    def close(self) -> None:
        self._sock.close()

    def __enter__(self) -> "TestbenchClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def _call(self, op: int, payload: bytes = b"") -> bytes:
        req = _REQ_HEADER.pack(TB_PROTO_VERSION, op) + payload
        try:
            self._sock.send(req)
            resp = self._sock.recv()
        except pynng.exceptions.NNGException as e:
            raise TestbenchIpcError(f"IPC call failed: {e}") from e
        if len(resp) < _RESP_HEADER.size:
            raise TestbenchIpcError("short response from daemon")
        _version, status = _RESP_HEADER.unpack_from(resp)
        if status != _STATUS_OK:
            raise TestbenchIpcError(f"daemon returned error status {status} for op {op}")
        return resp[_RESP_HEADER.size :]

    def ping(self) -> bool:
        try:
            self._call(_OP_PING)
            return True
        except TestbenchIpcError:
            return False

    def get_inputs(self) -> dict:
        """Returns {"bits": int, "ts_ms": int, "valid": bool}. bit i = input bit index i
        (absolute, matches io.map.inputs.labels bit indices directly).

        Raises TestbenchIpcError instead of returning a stale snapshot if the daemon's
        Modbus input poll isn't currently valid -- "valid" is always True when this
        returns rather than raising."""
        bits, ts_ms, valid = _INPUTS_RESP.unpack(self._call(_OP_GET_INPUTS))
        return {"bits": bits, "ts_ms": ts_ms, "valid": bool(valid)}

    def get_outputs(self) -> dict:
        """Returns {"bits": int, "min_addr": int, "span": int}. bit i of `bits` = coil
        (min_addr + i).

        Raises TestbenchIpcError if the daemon's last coil write didn't actually reach
        the bus -- the in-memory desired state wouldn't be a trustworthy snapshot of
        hardware reality right now."""
        bits, min_addr, span = _OUTPUTS_RESP.unpack(self._call(_OP_GET_OUTPUTS))
        return {"bits": bits, "min_addr": min_addr, "span": span}

    def set_coils_mask(self, mask: int, value: int) -> None:
        """Sets only the coils with their bit set in `mask` to the corresponding bit of
        `value`; bit i <-> coil (output_min_addr + i), per TestbenchLabels.coil_bit().

        Raises TestbenchIpcError, without applying anything, if the daemon's Modbus
        output link is currently down -- the write would never reach the hardware, so
        it's rejected outright rather than silently queued."""
        self._call(_OP_SET_COILS_MASK, _SET_COILS_REQ.pack(mask, value))

    def get_status(self) -> dict:
        uptime_ms, poll_count, poll_errors = _STATUS_RESP.unpack(self._call(_OP_GET_STATUS))
        return {"uptime_ms": uptime_ms, "poll_count": poll_count, "poll_errors": poll_errors}

    def iface_available(self, iface: int) -> tuple[bool, str]:
        """Is this one [iface.*] interface (TB_IFACE_CANBUS/RS422/RS485/RS232) available
        right now? Unlike every other method above, this one never raises -- it returns
        (False, "") uniformly whether the daemon didn't respond, the interface isn't
        configured in this stand's testbench.toml, or it's configured but not currently
        detected. Other test utilities are expected to treat all three the same way:
        this interface isn't usable right now. Mirrors ping()'s "always succeeds" style.
        Call ping() first if you need to tell "daemon down" apart from that.

        On success, returns (True, path) where path is the currently-resolved /dev
        path (e.g. "/dev/cu.usbserial-DN0536AY")."""
        try:
            present, path = _IFACE_STATUS_RESP.unpack(self._call(_OP_GET_IFACE_STATUS, _IFACE_STATUS_REQ.pack(iface)))
            if not present:
                return False, ""
            return True, path.split(b"\0", 1)[0].decode("ascii")
        except TestbenchIpcError:
            return False, ""


@dataclass(frozen=True)
class TestbenchLabels:
    """Label <-> address maps parsed straight from testbench.toml, mirroring
    testbench/io_hub/src/config.c's semantics -- including deriving the output coil
    span from the label table itself (io.map.outputs.start_address/count are parsed
    upstream but never actually used for addressing, same as today's testbench/io.py)."""

    input_bit: dict
    output_addr: dict
    output_min_addr: int
    output_span: int

    @classmethod
    def load(cls, config_path: str | Path) -> "TestbenchLabels":
        with open(config_path, "rb") as f:
            toml = tomllib.load(f)
        input_bit = {name: int(idx) for idx, name in toml["io"]["map"]["inputs"]["labels"].items()}
        output_addr = {name: int(addr) for addr, name in toml["io"]["map"]["outputs"]["labels"].items()}
        addrs = list(output_addr.values())
        min_addr = min(addrs) if addrs else 0
        span = (max(addrs) - min_addr + 1) if addrs else 0
        return cls(input_bit=input_bit, output_addr=output_addr, output_min_addr=min_addr, output_span=span)

    def decode_inputs(self, bits: int) -> dict:
        return {name: bool((bits >> idx) & 1) for name, idx in self.input_bit.items()}

    def decode_outputs(self, bits: int) -> dict:
        return {name: bool((bits >> (addr - self.output_min_addr)) & 1) for name, addr in self.output_addr.items()}

    def coil_bit(self, label: str) -> int:
        """Bit position relative to output_min_addr for `label`, as set_coils_mask()
        expects. Raises KeyError for an unknown label."""
        return self.output_addr[label] - self.output_min_addr

    def build_coil_request(self, assignments: dict) -> tuple:
        """{"LABEL": bool, ...} -> (mask, value) for set_coils_mask(). Raises ValueError
        if a label falls outside the 32-coil span the wire protocol can address."""
        mask = 0
        value = 0
        for label, state in assignments.items():
            bit = self.coil_bit(label)
            if not (0 <= bit < 32):
                raise ValueError(f"'{label}' is outside the 32-coil span this protocol can address")
            mask |= 1 << bit
            if state:
                value |= 1 << bit
        return mask, value


if __name__ == "__main__":
    import sys

    config_path = sys.argv[1] if len(sys.argv) > 1 else "testbench.toml"
    labels = TestbenchLabels.load(config_path)

    with TestbenchClient() as client:
        if not client.ping():
            sys.exit("testbench daemon not reachable on " + TB_IPC_DEFAULT_URL)

        status = client.get_status()
        print(f"uptime={status['uptime_ms']}ms poll_count={status['poll_count']} poll_errors={status['poll_errors']}")

        inputs = client.get_inputs()
        for name, on in sorted(labels.decode_inputs(inputs["bits"]).items()):
            print(f"  {name:<20} : {'ON' if on else 'off'}")
