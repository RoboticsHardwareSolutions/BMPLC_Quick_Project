"""HIL test of rhs_hal_can (CAN1) through the `can_hal` RTT CLI command
(user_tests/can_hal_test/target/can_hal_test.c) -- the HAL layer itself, not SLCAN or
usb_bridge. The bench's [iface.canbus] adapter (a CANable 2.0, slcan over a USB-CDC
virtual COM port, see testbench/testbench.toml's [iface.canbus]) is wired to the DUT's
physical CAN bus and plays the role of a second CAN node.

Runs against either board for the CLI-only tests (input validation, lifecycle guards -- no
real frame ever reaches the wire):

    PLC_TYPE=BMPLC_M|BMPLC_XL PLC_BIN=... uv run pytest user_tests/can_hal_test/testbench/ -v

but the real-traffic tests (actually sending/receiving a frame) are BMPLC_XL-only -- see
REQUIRES_REAL_TRAFFIC below. On BMPLC_M (STM32F103xE), bxCAN and USB share the same
dedicated 512-byte SRAM (RM0008). BMPLC_M's normal boot config keeps USB CDC NET up, and an
earlier run of this exact test proved the hardware erratum out: the *first* real CAN
transmission that actually got ACKed on the bus hung the whole MCU solid (even unrelated RTT
commands like `uptime` stopped answering) -- not a flood of bus errors, a dead board that
needed a power cycle. This is the same constraint usb_bridge_can.c's can_unsupported()
already rejects for non-App modes on this board, and the same one
user_tests/usb_bridge_test/testbench/test_usb_bridge_can_bridge.py already restricts its own
CAN Bridge E2E test to BMPLC_XL for. rhs_hal_can itself has no such guard (can_hal_test.c
calls it directly, unlike usb_bridge's mode-gated backend), so this test file is the one
place enforcing it for CAN.

Hardware precondition this test can't check in software, same as
test_usb_bridge_can_bridge.py: on BMPLC_XL the PG10 strap must be held high (bxCAN1 on
PD0/PD1, not the USB-shared PA11/PA12) and that pair must be wired to the bench's
[iface.canbus] segment.

A plain `pytest` run with no PLC_TYPE/JLINK_SERIAL set just skips (see root conftest's
`hil_available()`); with hardware but no bench canbus adapter detected, the real-traffic
tests skip but the CLI-only tests still run.
"""

from __future__ import annotations

import os
import re
import threading
import time
from typing import Iterator

import pytest

import testbench_client  # name kept off the module namespace: pytest would otherwise
# try to collect testbench_client.TestbenchClient as a test class, since its name
# matches the default `Test*` python_classes pattern.
from conftest import hil_available

can = pytest.importorskip("can")

pytestmark = pytest.mark.skipif(
    not hil_available(),
    reason="can_hal tests need RTT: set PLC_TYPE (HIL stand) or JLINK_SERIAL and MCU",
)

REQUIRES_REAL_TRAFFIC = pytest.mark.skipif(
    os.environ.get("PLC_TYPE") != "BMPLC_XL" and not os.environ.get("CAN_HAL_ALLOW_M_TRAFFIC"),
    reason="real CAN traffic on BMPLC_M can hang the MCU solid: bxCAN and USB share SRAM on "
    "STM32F103 (RM0008) and USB CDC NET is always up on this board -- see the module "
    "docstring. BMPLC_XL only, unless CAN_HAL_ALLOW_M_TRAFFIC=1 is set -- a deliberate "
    "escape hatch for one-off verification against an M build with USB/can_open compiled "
    "out (e.g. toolchains/plc_m_canhal_oneoff.cmake), not for the board's normal firmware.",
)

BITRATE = 500000
RX_TIMEOUT_S = 1.0
RX_POLL_INTERVAL_S = 0.05

_STAT_RE = re.compile(
    r"tx_msgs=(\d+) tx_errs=(\d+) tx_ovfs=(\d+) rx_msgs=(\d+) rx_errs=(\d+) rx_ovfs=(\d+) "
    r"sce=(\d+) busoff=(\d+) rx_drops=(\d+)"
)
_RX_RE = re.compile(r"id=([0-9a-f]+) ext=([01]) rtr=([01]) len=(\d+) data=([0-9a-f]*)")


def _stat(plc, timeout: float = 5.0) -> dict[str, int]:
    out = plc.run("can_hal stat", timeout=timeout)
    m = _STAT_RE.search(out)
    assert m, f"unexpected 'can_hal stat' output: {out!r}"
    keys = ("tx_msgs", "tx_errs", "tx_ovfs", "rx_msgs", "rx_errs", "rx_ovfs", "sce", "busoff", "rx_drops")
    return dict(zip(keys, (int(g) for g in m.groups())))


def _stat_or_none(plc, timeout: float = 5.0) -> dict[str, int] | None:
    """Like _stat(), but returns None instead of asserting when the response doesn't parse --
    for polling during an active error storm, where a `can_hal stat` round trip can occasionally
    come back as nothing but interleaved error-log noise."""
    out = plc.run("can_hal stat", timeout=timeout)
    m = _STAT_RE.search(out)
    if not m:
        return None
    keys = ("tx_msgs", "tx_errs", "tx_ovfs", "rx_msgs", "rx_errs", "rx_ovfs", "sce", "busoff", "rx_drops")
    return dict(zip(keys, (int(g) for g in m.groups())))


def _poll_rx(plc, timeout: float = RX_TIMEOUT_S) -> dict | None:
    """Poll `can_hal rx` until a frame shows up or `timeout` elapses. Returns a dict with
    id/ext/rtr/len/data, or None if nothing arrived -- the RTT round trip (tens of ms) is
    slower than the bus, so a single poll right after sending can race the ISR."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        out = plc.run("can_hal rx")
        m = _RX_RE.search(out)
        if m:
            return {
                "id": int(m.group(1), 16),
                "ext": m.group(2) == "1",
                "rtr": m.group(3) == "1",
                "len": int(m.group(4)),
                "data": m.group(5),
            }
        if "none" not in out:
            pytest.fail(f"unexpected 'can_hal rx' output: {out!r}")
        time.sleep(RX_POLL_INTERVAL_S)
    return None


def recv_frames(bus, count: int, timeout: float) -> list:
    """Collect up to `count` CAN frames from `bus` within `timeout` seconds (python-can Bus)."""
    frames = []
    deadline = time.monotonic() + timeout
    while len(frames) < count and time.monotonic() < deadline:
        msg = bus.recv(0.1)
        if msg is not None:
            frames.append(msg)
    return frames


@pytest.fixture(scope="module")
def canbus_port(tb_client: "testbench_client.TestbenchClient") -> str:
    present, path = tb_client.iface_available(testbench_client.TB_IFACE_CANBUS)
    if not present:
        pytest.skip("bench [iface.canbus] adapter not present")
    return path


@pytest.fixture
def canbus_bus(canbus_port: str) -> Iterator["can.BusABC"]:
    bus = can.Bus(interface="slcan", channel=canbus_port, bitrate=BITRATE, sleep_after_open=0.2)
    try:
        recv_frames(bus, 1000, 0.2)  # flush anything already on the bus
        yield bus
    finally:
        bus.shutdown()


@pytest.fixture(scope="module")
def can_hal(plc) -> Iterator[None]:
    """Module-scoped rather than one init/deinit per test: on BMPLC_M, a *second* CAN1
    init/deinit cycle in the same session was found to silently stop answering RTT entirely
    (no real bus traffic involved -- just init, then deinit, then init again), consistent with
    the module docstring's bxCAN/USB shared-SRAM erratum reaching further than "only real
    traffic is risky." Tests that need their own fresh init (reinit cycling, the baud sweep,
    bus-off) already manage that explicitly and don't rely on this fixture for it."""
    out = plc.run_until(f"can_hal init {BITRATE}", "started")
    assert "started" in out, out
    try:
        yield
    finally:
        plc.run("can_hal deinit")


# --------------------------------------------------------------------------------------
# CLI-only: input validation and lifecycle guards. No real frame ever reaches the wire,
# so these run on BMPLC_M too (RHS_HAL_CAN init/deinit alone is safe there -- only real
# bus traffic while USB is up triggers the erratum, see the module docstring).
# --------------------------------------------------------------------------------------


def _run_until(plc, cmd: str, expect: str, timeout: float = 25.0) -> str:
    """A generously-timed plc.run(): BMPLC_M was found to go RTT-unresponsive for stretches of
    several seconds at a time even for commands that never touch CAN hardware at all (e.g. two
    consecutive out-of-range `tx` rejections, both hitting the same early return before any
    rhs_hal_can call) -- almost certainly USB CDC NET's network stack doing something blocking
    on this board, unrelated to CAN. Deliberately plc.run(), not plc.run_until(): the latter
    budgets its *own* `timeout` for the initial run() call and only then starts "retrying" with
    whatever's left of the same deadline, which is ~nothing once that first run() already ate
    the whole timeout waiting through a stall -- plain run() with one generous timeout actually
    waits that long."""
    out = plc.run(cmd, timeout=timeout)
    assert expect in out, out
    return out


def test_init_rejects_bad_baud(plc) -> None:
    _run_until(plc, "can_hal init not_a_number", "bad baud")


def test_commands_before_init_report_not_running(plc) -> None:
    _run_until(plc, "can_hal rx", "not running")
    _run_until(plc, "can_hal deinit", "not running")
    _run_until(plc, "can_hal tx 123 0 0", "not running")


def test_tx_rejects_out_of_range_ids(plc, can_hal) -> None:
    """11-bit standard / 29-bit extended ceilings -- rejected before rhs_hal_can_tx() is ever
    called, so no frame goes out and this is safe without REQUIRES_REAL_TRAFFIC."""
    _run_until(plc, "can_hal tx 800 0 0", "bad id")  # 0x800 > std max 0x7FF
    _run_until(plc, "can_hal tx 20000000 1 0", "bad id")  # 0x20000000 > ext max 0x1FFFFFFF


def test_tx_rejects_malformed_id(plc, can_hal) -> None:
    _run_until(plc, "can_hal tx 123x 0 0", "bad id")  # trailing garbage after the hex id


def test_tx_rejects_malformed_ext_rtr_flags(plc, can_hal) -> None:
    _run_until(plc, "can_hal tx 123 x 0", "bad args")
    _run_until(plc, "can_hal tx 123 0 2", "bad args")
    _run_until(plc, "can_hal tx 123 01 0", "bad args")


def test_tx_rejects_malformed_data(plc, can_hal) -> None:
    _run_until(plc, "can_hal tx 123 0 0 010", "bad data")  # odd number of hex digits
    _run_until(plc, "can_hal tx 123 0 0 0102030405060708AA", "bad data")  # 9 bytes, 1 past DLC max
    _run_until(plc, "can_hal tx 123 0 0 zz", "bad data")  # not hex at all


# --------------------------------------------------------------------------------------
# Real traffic: BMPLC_XL only (or BMPLC_M with CAN_HAL_ALLOW_M_TRAFFIC=1 against a
# USB-disabled one-off build -- see the module docstring).
# --------------------------------------------------------------------------------------


@REQUIRES_REAL_TRAFFIC
def test_device_to_bench_standard_frame(plc, canbus_bus, can_hal) -> None:
    out = plc.run("can_hal tx 123 0 0 01020304")
    assert "tx ok" in out, out

    [frame] = recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
    assert frame.arbitration_id == 0x123
    assert not frame.is_extended_id
    assert not frame.is_remote_frame
    assert bytes(frame.data) == bytes([0x01, 0x02, 0x03, 0x04])


@REQUIRES_REAL_TRAFFIC
def test_bench_to_device_standard_frame(plc, canbus_bus, can_hal) -> None:
    msg = can.Message(arbitration_id=0x456, data=[5, 6, 7], is_extended_id=False)
    canbus_bus.send(msg)

    frame = _poll_rx(plc)
    assert frame is not None, "device never reported a received frame"
    assert frame["id"] == 0x456
    assert frame["ext"] is False
    assert frame["rtr"] is False
    assert frame["len"] == 3
    assert frame["data"] == "050607"


@REQUIRES_REAL_TRAFFIC
def test_extended_id_round_trip(plc, canbus_bus, can_hal) -> None:
    out = plc.run("can_hal tx 1abcdef0 1 0 aabb")
    assert "tx ok" in out, out
    [frame] = recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
    assert frame.arbitration_id == 0x1ABCDEF0
    assert frame.is_extended_id
    assert bytes(frame.data) == bytes([0xAA, 0xBB])

    msg = can.Message(arbitration_id=0x1FFFFFFF, data=[], is_extended_id=True)
    canbus_bus.send(msg)
    frame = _poll_rx(plc)
    assert frame is not None, "device never reported the extended-ID frame"
    assert frame["id"] == 0x1FFFFFFF
    assert frame["ext"] is True
    assert frame["len"] == 0


@REQUIRES_REAL_TRAFFIC
def test_rtr_frame_round_trip(plc, canbus_bus, can_hal) -> None:
    out = plc.run("can_hal tx 42 0 1")  # RTR, DLC 0 (no payload on the wire)
    assert "tx ok" in out, out
    [frame] = recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
    assert frame.arbitration_id == 0x42
    assert frame.is_remote_frame

    msg = can.Message(arbitration_id=0x99, is_extended_id=False, is_remote_frame=True, dlc=4)
    canbus_bus.send(msg)
    frame = _poll_rx(plc)
    assert frame is not None, "device never reported the RTR frame"
    assert frame["id"] == 0x99
    assert frame["rtr"] is True


@REQUIRES_REAL_TRAFFIC
def test_max_payload_and_id_boundaries(plc, canbus_bus, can_hal) -> None:
    """DLC=8 (the most a classic CAN frame ever carries) and the exact std/ext ID ceilings
    (0x7FF / 0x1FFFFFFF) -- every round-trip test above uses a handful of bytes and small
    IDs, so the boundaries themselves were never actually put on the wire."""
    out = plc.run("can_hal tx 7ff 0 0 0102030405060708")
    assert "tx ok" in out, out
    [frame] = recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
    assert frame.arbitration_id == 0x7FF
    assert not frame.is_extended_id
    assert bytes(frame.data) == bytes(range(1, 9))

    msg = can.Message(arbitration_id=0x7FF, data=list(range(1, 9)), is_extended_id=False)
    canbus_bus.send(msg)
    frame = _poll_rx(plc)
    assert frame is not None, "device never reported the max-DLC std-ID frame"
    assert frame["id"] == 0x7FF
    assert frame["len"] == 8
    assert frame["data"] == "0102030405060708"

    out = plc.run("can_hal tx 1fffffff 1 0 aabbccddeeff0011")
    assert "tx ok" in out, out
    [frame] = recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
    assert frame.arbitration_id == 0x1FFFFFFF
    assert frame.is_extended_id
    assert bytes(frame.data) == bytes.fromhex("aabbccddeeff0011")


@REQUIRES_REAL_TRAFFIC
def test_statistics_increment(plc, canbus_bus, can_hal) -> None:
    """Counters are cumulative for the whole `can_hal` session -- just check they moved
    after known device-side tx/rx, not exact values (other tests in this module may
    have already pushed traffic)."""
    before = _stat(plc)

    plc.run("can_hal tx 321 0 0 09")
    recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
    canbus_bus.send(can.Message(arbitration_id=0x654, data=[8], is_extended_id=False))
    _poll_rx(plc)

    after = _stat(plc)
    assert after["tx_msgs"] > before["tx_msgs"], (before, after)
    assert after["rx_msgs"] > before["rx_msgs"], (before, after)


@REQUIRES_REAL_TRAFFIC
def test_reinit_after_deinit(plc, canbus_bus, can_hal) -> None:
    """can_hal init on an already-running channel (the `can_hal` fixture's init, run once
    more here) must deinit first rather than asserting -- the usb_bridge CAN backend relies
    on the same rhs_hal_can_init()-after-rhs_hal_can_deinit() sequence on every open/close."""
    out = plc.run_until(f"can_hal init {BITRATE}", "started")
    assert "started" in out, out

    out = plc.run("can_hal tx 1 0 0 ff")
    assert "tx ok" in out, out
    [frame] = recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
    assert frame.arbitration_id == 0x1
    assert bytes(frame.data) == bytes([0xFF])


@REQUIRES_REAL_TRAFFIC
def test_multiple_reinit_cycles(plc, canbus_bus) -> None:
    """3 consecutive init/tx/rx/deinit cycles -- test_reinit_after_deinit above only proves
    one re-init survives; this checks the HAL and this module's own queue/callback
    registration don't leak or degrade over several.

    Ends with a plain init rather than the loop's own deinit: `can_hal` is module-scoped (see
    its own docstring) on the assumption the channel is left running at BITRATE for whichever
    test needs it next, and this test manages init/deinit itself rather than depending on that
    fixture -- leaving the channel off would silently break that assumption for later tests."""
    for i in range(3):
        out = plc.run_until(f"can_hal init {BITRATE}", "started")
        assert "started" in out, out

        out = plc.run(f"can_hal tx {0x10 + i:x} 0 0 {i:02x}")
        assert "tx ok" in out, out
        [frame] = recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
        assert frame.arbitration_id == 0x10 + i
        assert bytes(frame.data) == bytes([i])

        canbus_bus.send(can.Message(arbitration_id=0x20 + i, data=[i], is_extended_id=False))
        frame = _poll_rx(plc)
        assert frame is not None, f"cycle {i}: device never reported the received frame"
        assert frame["id"] == 0x20 + i

        out = plc.run("can_hal deinit")
        assert "stopped" in out, out

    out = plc.run_until(f"can_hal init {BITRATE}", "started")
    assert "started" in out, out


@REQUIRES_REAL_TRAFFIC
@pytest.mark.parametrize("baud", [125000, 250000, 1000000], ids=["125k", "250k", "1M"])
def test_baud_rate_sweep(plc, canbus_port: str, baud: int) -> None:
    """Every other test in this module runs at BITRATE (500000) only. rhs_hal_can_init()'s own
    doc warns that a valid bit-timing split isn't guaranteed for every baud on every
    peripheral clock ("Returns false ... if no valid bit-timing exists for baud on this
    peripheral's clock"), so a few other common CAN bitrates get a real round trip here,
    independent of the module-wide `can_hal`/`canbus_bus` fixtures (both pinned to BITRATE).

    Restores a plain BITRATE init in `finally` after its own deinit, for the same reason
    test_multiple_reinit_cycles does: `can_hal` being module-scoped means whatever this test
    leaves behind is what the *next* test relying on that fixture inherits."""
    out = plc.run_until(f"can_hal init {baud}", "started")
    assert "started" in out, out
    bus = can.Bus(interface="slcan", channel=canbus_port, bitrate=baud, sleep_after_open=0.2)
    try:
        recv_frames(bus, 1000, 0.2)  # flush anything already on the bus

        out = plc.run("can_hal tx 10 0 0 ab")
        assert "tx ok" in out, out
        [frame] = recv_frames(bus, 1, RX_TIMEOUT_S)
        assert frame.arbitration_id == 0x10
        assert bytes(frame.data) == bytes([0xAB])

        bus.send(can.Message(arbitration_id=0x20, data=[0xCD], is_extended_id=False))
        frame = _poll_rx(plc)
        assert frame is not None, f"device never reported a frame at {baud} baud"
        assert frame["id"] == 0x20
        assert frame["data"] == "cd"
    finally:
        bus.shutdown()
        plc.run("can_hal deinit")
        plc.run_until(f"can_hal init {BITRATE}", "started")


@REQUIRES_REAL_TRAFFIC
def test_tx_mailbox_overflow(plc, can_hal) -> None:
    """Loads all 3 bxCAN TX mailboxes with no bench listener acking them, via `txburst` (4
    frames, one CLI call, no RTT round trip between them, reporting ok/failed/tx_ovfs all in
    its one response -- see can_hal_test.c's can_hal_cmd_txburst). Expects exactly 3 ok + 1
    failed, the 4th overflowing all 3 mailboxes (RHSHalCANStatistic.tx_ovfs incrementing,
    rhs_hal_can.c's rcan_send()==false path) -- not exercised by any other test in this module.

    What this test deliberately does NOT do, and why: the obvious next step would be to let the
    resulting retry/ack-error storm run until bus-off (rhs_hal_can.h's documented SCE event) and
    then confirm ABOM's automatic recovery. A manual probe outside pytest proved that doesn't
    happen in any bounded time: tec parks at the error-passive threshold (128) and sits there
    for 60+ real seconds without ever reaching bus-off (256) -- a lone error-passive
    transmitter whose only error is an ACK error, seeing no dominant bit while sending its own
    passive error flag, is specifically exempted from TEC incrementing further by the CAN
    fault-confinement spec (see test_bus_off_via_duplicate_id's docstring for the real way to
    reach bus-off). So this test stops at the one thing that scenario reliably produces --
    tx_ovfs -- rather than chasing bus-off itself.

    This used to also need a `CAN_HAL_ALLOW_BUSOFF_STORM` opt-in: before rhs_hal_can.c's
    SCE logging was rate-limited (see TODO.md history / git log), the retry storm logged on
    every single retry -- thousands/second, 100+ KB/s over RTT -- and could leave the board's
    RTT/CLI link unresponsive for a long, unbounded time. That's fixed now (logging only
    happens when lec/tec/rec actually change, which settles almost immediately), so the
    storm itself is no longer a hang risk. What *can* still happen, briefly, while tec is still
    climbing toward 128: the SCE ISR's own logging for a genuine state change can preempt this
    test's `txburst` response mid-printf, splitting e.g. "failed=" from its own digit. That's
    why the three fields below are parsed independently rather than with one contiguous regex
    -- each field is still there, just not necessarily adjacent to the others in the text.

    The `finally` below (deinit, then re-init) hands back a working channel for later tests:
    `can_hal` is module-scoped (see its own docstring), so its teardown only runs once at the
    very end of the module, long after a later test in this file would need the channel back."""
    before_text = plc.run("can_hal stat", timeout=5.0)
    before = _STAT_RE.search(before_text)
    assert before, f"unexpected 'can_hal stat' output: {before_text!r}"
    before_tx_ovfs = int(before.group(3))

    try:
        out = plc.run("can_hal txburst 4 799 0 0", timeout=10.0)
        m_ok = re.search(r"ok=(\d+)", out)
        m_failed = re.search(r"failed=(\d+)", out)
        m_ovfs = re.search(r"tx_ovfs=(\d+)", out)
        assert m_ok and m_failed and m_ovfs, f"unexpected 'can_hal txburst' output: {out!r}"
        ok, failed, tx_ovfs = int(m_ok.group(1)), int(m_failed.group(1)), int(m_ovfs.group(1))
        assert ok == 3, (ok, failed, tx_ovfs)
        assert failed == 1, (ok, failed, tx_ovfs)
        assert tx_ovfs > before_tx_ovfs, (before_tx_ovfs, tx_ovfs)
    finally:
        plc.run("can_hal deinit", timeout=15.0)
        plc.run_until(f"can_hal init {BITRATE}", "started", timeout=15.0)


BUSOFF_DUPLICATE_ID = 0x100


class _DuplicateIdSender:
    """Keeps sending an empty frame (DLC=0) at BUSOFF_DUPLICATE_ID back to back, as fast as the
    adapter allows, in a background thread until stopped.

    test_bus_off_via_duplicate_id collides this against the device's own txburst sends of the
    *same* arbitration ID with a non-empty payload (DLC=8): the arbitration field (ID+RTR+IDE)
    is bit-for-bit identical on both sides, so neither side backs off there -- both continue
    into the DLC field still believing they're the sole transmitter. DLC=0 is encoded "0000"
    (all dominant); DLC=8 is "1000" (first bit recessive). So at that very first DLC bit the
    device sends recessive while the bus (bench driving dominant) reads back dominant: a
    genuine bit error for the device specifically, confirmed empirically to drive bus-off
    within a couple of `txburst` rounds -- see test_bus_off_via_duplicate_id's docstring for why
    this works where a gross baud-rate mismatch (tried first, discarded) did not."""

    def __init__(self, bus: "can.BusABC") -> None:
        self._bus = bus
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        msg = can.Message(arbitration_id=BUSOFF_DUPLICATE_ID, data=[], is_extended_id=False)
        while not self._stop.is_set():
            try:
                self._bus.send(msg)
            except can.CanError:
                pass  # the bus is deliberately being driven into errors; dropped sends are expected

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)


@REQUIRES_REAL_TRAFFIC
def test_bus_off_via_duplicate_id(plc, canbus_bus, can_hal) -> None:
    """Drives a *real* bus-off, unlike test_tx_mailbox_overflow above. That test's unacked,
    otherwise-silent bus never reaches bus-off because of a specific CAN fault-confinement
    exception (Bosch CAN 2.0 / ISO 11898-1): a lone error-passive transmitter whose only error
    is an ACK error, and which sees no dominant bit while sending its own passive error flag,
    does not have its TEC incremented at all -- there being nobody else on the bus is exactly
    the condition that exception exists for, by design, so TEC parks at 128 forever (confirmed
    with a 60-second manual probe before settling on the approach used here).

    A gross baud-rate mismatch was tried next (bench hammering the bus at a different standard
    bitrate than the device) hoping for genuine bit-level collisions -- also discarded, by
    design rather than bad luck: bit stuffing caps run lengths so a slower device's frame never
    looks "idle" to a faster listener for long, and a CAN controller only starts a new
    transmission once it has observed the bus idle in the first place, so two uncorrelated,
    well-behaved controllers mostly just take turns instead of colliding.

    What actually works, used here: the bench (via _DuplicateIdSender) and the device (via
    `txburst ... 8`, see its docstring) both send the *same* arbitration ID, at the *same*
    baud, back to back -- with different DLCs, so the first bit where they'd otherwise be
    forced to diverge is a genuine bit error for the device, not just a non-ack. tx_ovfs from
    test_tx_mailbox_overflow isn't expected here (txburst's own mailboxes drain normally once
    the device loses/errors each attempt, unlike the forever-stuck no-listener case).

    Recovery is checked the way rhs_hal_can.h documents it: bxCAN's ABOM clears bus-off
    automatically once the bus is idle, no rhs_hal_can_init() call needed in between."""
    sender = _DuplicateIdSender(canbus_bus)
    try:
        sender.start()

        deadline = time.monotonic() + 15.0
        busoff = 0
        while busoff == 0 and time.monotonic() < deadline:
            plc.run(f"can_hal txburst 3 {BUSOFF_DUPLICATE_ID:x} 0 0 8", timeout=5.0)
            stat = _stat_or_none(plc, timeout=5.0)
            busoff = stat["busoff"] if stat is not None else 0
        assert busoff > 0, "bus-off was never reported despite the duplicate-ID collision"
    finally:
        sender.stop()

    # Recovery: ABOM clears bus-off automatically once the bus is idle -- no re-init needed,
    # just give it a moment with the colliding sender stopped, then prove it with a real frame.
    time.sleep(0.5)
    recv_frames(canbus_bus, 1000, 0.2)  # flush
    out = plc.run("can_hal tx 7a1 0 0 01", timeout=5.0)
    assert "tx ok" in out, out
    [frame] = recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
    assert frame.arbitration_id == 0x7A1
    assert bytes(frame.data) == bytes([0x01])


@REQUIRES_REAL_TRAFFIC
def test_rx_queue_overflow(plc, canbus_bus, can_hal) -> None:
    """Floods CAN_HAL_TEST_RX_QUEUE_LEN (32) + a few more frames from the bench without ever
    draining via `can_hal rx` in between: rhs_message_queue_put() in the RX ISR must start
    failing, counted by this module's own rx_drops (distinct from the hardware FIFO's
    rx_ovfs, which nothing here is expected to trip) -- and the queue must keep working
    normally once drained, not get stuck from the overflow."""
    before = _stat(plc)
    flood_count = 40
    for i in range(flood_count):
        canbus_bus.send(can.Message(arbitration_id=0x500 + i, data=[i & 0xFF], is_extended_id=False))
    time.sleep(1.0)  # let the RX ISR and queue puts settle before reading stat

    mid = _stat(plc)
    assert mid["rx_drops"] > before["rx_drops"], (
        f"expected some of {flood_count} frames to overflow the 32-deep rx_queue: {before} -> {mid}"
    )

    drained = 0
    while _poll_rx(plc, timeout=0.5) is not None:
        drained += 1
    assert drained > 0, "rx_queue produced nothing at all after the flood"

    # Still functional afterwards
    canbus_bus.send(can.Message(arbitration_id=0x5FF, data=[0xAA], is_extended_id=False))
    frame = _poll_rx(plc)
    assert frame is not None, "rx_queue did not recover after draining the overflow"
    assert frame["id"] == 0x5FF
