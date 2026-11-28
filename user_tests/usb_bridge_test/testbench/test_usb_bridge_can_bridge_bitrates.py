"""HIL sweep of the CAN bitrates usb_bridge's CAN Bridge mode on BMPLC_XL (the production `usb can bridge
<baud>` CLI) actually interoperates with on this bench. See test_usb_bridge_can_bridge.py for the
fixture/hardware-precondition background shared with this file.

Swept rates: 7 of the 9 standard Lawicel 'S' bitrates -- python-can's own `can.interfaces.slcan.slcanBus
._BITRATES` table (10000/20000/50000/100000/125000/250000/500000/750000/1000000) minus 10000 and 750000.
Both open cleanly (`rhs_hal_can_init()`/`rcan_start()` reports a clean error instead of crashing when no exact
bit-timing exists, thirdparty/rhs/hal/rhs_hal_can/rhs_hal_can.c) but never actually exchange a frame on real
hardware with the bench's CANable 2.0 adapter -- 10000 bps because BMPLC_XL's own bxCAN has no exact integer
(prescaler, BS1, BS2) solution for it, 750000 bps because CANable 2.0's own slcan firmware hard-codes a timing
its own source flags `// THIS IS VERY INACCURATE!!! FIXME`, so the two sides' actual bit rates differ enough to
never ACK each other. See thirdparty/rhs/applications/services/usb_bridge/README.md's "Bitrate limitations"
section and TODO.md for the full writeup; not a crash, not fixable in our firmware, just excluded from this
sweep since every case would fail the same documented way.

`usb_bridge_cli.c`'s trailing baud token goes straight through `atoi()` with no range check into
`usb_bridge_start()` -> `rhs_hal_can_init()` -> `rcan_start()` (thirdparty/rcan/rcan_timing.c's generic
prescaler/BS1/BS2 search, which can legitimately fail to find an exact-integer solution for an arbitrary
(peripheral clock, target bitrate) pair) -> a clean `false` return, surfaced here as a plain failed frame
exchange rather than a board crash (see rhs_hal_can.c's `rhs_hal_can_init()` -- it used to `rhs_assert` on this
and hard-crash the MCU; fixed to return false instead).

Crash detection: `PlcRtt.run()`/`run_until()` (testbench/pyhil/rtt.py) NEVER raise, even on a pure timeout --
they just return whatever text accumulated. A hard assert's log line ("...Message: Assert. Called from
file: ..., line: ...", thirdparty/rhs/core/check.c) is written to the RTT buffer before the core halts, so it
reliably shows up in that returned text instead of the expected "started can bridge" marker.
`usb_bridge_hw.bridge_start()`'s own `assert started_marker in out, out` then raises a plain AssertionError
whose message *is* that RTT text -- this file classifies that message (does it contain "Assert"/"Message:"?)
to distinguish "the board crashed" from "something else went wrong starting the bridge." Kept as a defensive
check even though no swept rate is currently known to trigger it (a future untested/arbitrary rate could).

Crash policy: abort-and-skip. If a bitrate crashes the board, every remaining bitrate in the sweep is skipped
rather than attempted against a halted core (which would otherwise produce a cascade of confusing, unrelated
RTT-timeout failures). A future improvement would add a `PlcRtt.recover()` (reset without reflash + re-poll for
the boot banner, mirroring conftest.py's own plc fixture retry loop) to resume the sweep after a crash instead
of abandoning the rest of the ladder -- not implemented here; flagged as a known limitation of this first
version.

    PLC_TYPE=BMPLC_XL PLC_BIN=... uv run pytest user_tests/usb_bridge_test/testbench/test_usb_bridge_can_bridge_bitrates.py -v
"""

from __future__ import annotations

import os
from typing import Iterator

import pytest

import usb_bridge_hw as hw

can = pytest.importorskip("can")

pytestmark = pytest.mark.skipif(
    os.environ.get("PLC_TYPE") != "BMPLC_XL",
    reason="CAN Bridge E2E needs the HIL stand's [iface.canbus] adapter; BMPLC_XL only -- "
    "BMPLC_M rejects CAN Bridge (see test_usb_bridge_cli.py)",
)

# 10000 and 750000 bps deliberately excluded -- known, documented non-interop with the bench's CANable 2.0
# adapter, not a crash risk; see this module's docstring and README.md's "Bitrate limitations" section.
# Ordered from already-proven-safe/datasheet-called-out rates toward the untested extremes -- see module
# docstring's "Crash policy" paragraph for why order matters here.
SLCAN_BITRATES = [500000, 125000, 250000, 1000000, 20000, 50000, 100000]

RX_TIMEOUT_S = 1.0

# Set to the first bitrate that hard-crashes the board, or None. A plain list (not a bool) so the message
# survives into every subsequent case's skip reason.
_board_dead: list[str] = []


@pytest.fixture(scope="module")
def canbus_port(tb_client) -> str:
    path = hw.canbus_port(tb_client)
    if path is None:
        pytest.skip("bench [iface.canbus] adapter not present")
    return path


@pytest.mark.parametrize("bitrate", SLCAN_BITRATES, ids=lambda b: f"{b}bps")
def test_bridge_bitrate(
    plc, io_config, request: pytest.FixtureRequest, canbus_port: str, bitrate: int
) -> None:
    if _board_dead:
        pytest.skip(f"board hard-crashed earlier in this sweep (at {_board_dead[0]} bps) -- skipping")

    try:
        hw.bridge_start(plc, "bridge", io_config, request, baud=bitrate)
    except AssertionError as e:
        text = str(e)
        if "Assert" in text or "Message:" in text:
            _board_dead.append(f"{bitrate}")
            pytest.fail(f"bridge firmware CRASHED starting Bridge mode at {bitrate} bps:\n{text}", pytrace=False)
        pytest.fail(f"bridge did not start at {bitrate} bps (no crash marker seen):\n{text}", pytrace=False)

    try:
        plc_bus = can.Bus(interface="slcan", channel=hw.PORT, bitrate=bitrate, sleep_after_open=0.2)
        canbus_bus = can.Bus(
            interface="slcan", channel=canbus_port, bitrate=bitrate, sleep_after_open=0.2
        )
        try:
            hw.recv_frames(plc_bus, 1000, 0.2)
            hw.recv_frames(canbus_bus, 1000, 0.2)

            msg = can.Message(arbitration_id=0x123, data=[1, 2, 3, 4], is_extended_id=False)
            plc_bus.send(msg)
            [frame] = hw.recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
            assert frame.arbitration_id == msg.arbitration_id
            assert bytes(frame.data) == bytes(msg.data)

            msg2 = can.Message(arbitration_id=0x456, data=[5, 6], is_extended_id=False)
            canbus_bus.send(msg2)
            [frame2] = hw.recv_frames(plc_bus, 1, RX_TIMEOUT_S)
            assert frame2.arbitration_id == msg2.arbitration_id
            assert bytes(frame2.data) == bytes(msg2.data)
        finally:
            plc_bus.shutdown()
            canbus_bus.shutdown()
    finally:
        hw.bridge_stop(plc, io_config, request)
