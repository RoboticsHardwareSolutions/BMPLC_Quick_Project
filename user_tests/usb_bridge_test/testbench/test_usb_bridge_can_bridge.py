"""HIL end-to-end test of usb_bridge, CAN target in Bridge mode (the production `usb can bridge` CLI, NOT
usb_bridge_echo). Needs the HIL stand specifically, not just RTT: the bench's [iface.canbus] adapter (a
CANable 2.0, slcan over a USB-CDC virtual COM port) is the only way to exercise the physical side of the bridge,
and only BMPLC_XL supports CAN Bridge mode at all -- BMPLC_M rejects it outright (CAN and USB share SRAM on
STM32F103, see test_usb_bridge_cli.py's UNSUPPORTED table for that assertion).

Bridge mode is a pure pass-through in both directions (usb_bridge_i.h's has_app() is false for this mode, so the
echo callback used by the App-mode tests never runs here): a frame written on one side appears unmodified on the
other, nothing more. Compare against test_usb_bridge_can_both.py for the Both/BridgeApp-mode routing, which layers
an echo reply on top of this same pass-through.

Hardware precondition this test can't check in software: BMPLC_XL's PG10 strap must be held high (bxCAN1 on
PD0/PD1, not the USB-shared PA11/PA12) and PD0/PD1 must be physically wired to the bench's [iface.canbus] segment
(see usb_bridge.c's usb_bridge_check()/the "USB is not available" error). If it isn't, bridge_start() below fails
loudly on that error string rather than silently passing.

    PLC_TYPE=BMPLC_XL PLC_BIN=... uv run pytest user_tests/usb_bridge_test/testbench/test_usb_bridge_can_bridge.py -v
"""

from __future__ import annotations

import os
import re
import time
from typing import Iterator

import pytest

import usb_bridge_hw as hw

can = pytest.importorskip("can")

pytestmark = pytest.mark.skipif(
    os.environ.get("PLC_TYPE") != "BMPLC_XL",
    reason="CAN Bridge E2E needs the HIL stand's [iface.canbus] adapter; BMPLC_XL only -- "
    "BMPLC_M rejects CAN Bridge (see test_usb_bridge_cli.py)",
)

BITRATE = 500000
RX_TIMEOUT_S = 1.0
BURST_COUNT = 20


@pytest.fixture(scope="module")
def canbus_port(tb_client) -> str:
    path = hw.canbus_port(tb_client)
    if path is None:
        pytest.skip("bench [iface.canbus] adapter not present")
    return path


@pytest.fixture
def canbus_bus(canbus_port: str) -> Iterator[can.BusABC]:
    b = can.Bus(interface="slcan", channel=canbus_port, bitrate=BITRATE, sleep_after_open=0.2)
    try:
        hw.recv_frames(b, 1000, 0.2)  # flush anything already on the bus
        yield b
    finally:
        b.shutdown()


@pytest.fixture(scope="module", autouse=True)
def bridge_can(plc, io_config, request: pytest.FixtureRequest) -> Iterator[None]:
    hw.bridge_start(plc, "bridge", io_config, request)
    yield
    hw.bridge_stop(plc, io_config, request)


@pytest.fixture
def plc_bus() -> Iterator[can.BusABC]:
    b = can.Bus(interface="slcan", channel=hw.PORT, bitrate=BITRATE, sleep_after_open=0.2)
    try:
        hw.recv_frames(b, 1000, 0.2)  # flush anything already queued
        yield b
    finally:
        b.shutdown()


def test_usb_to_device(plc_bus: can.BusABC, canbus_bus: can.BusABC) -> None:
    msg = can.Message(arbitration_id=0x123, data=[1, 2, 3, 4], is_extended_id=False)
    plc_bus.send(msg)
    [frame] = hw.recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
    assert frame.arbitration_id == msg.arbitration_id
    assert bytes(frame.data) == bytes(msg.data)
    assert not hw.recv_frames(plc_bus, 1, 0.3), "nothing should come back on the USB side"


def test_device_to_usb(plc_bus: can.BusABC, canbus_bus: can.BusABC) -> None:
    msg = can.Message(arbitration_id=0x456, data=[5, 6, 7], is_extended_id=False)
    canbus_bus.send(msg)
    [frame] = hw.recv_frames(plc_bus, 1, RX_TIMEOUT_S)
    assert frame.arbitration_id == msg.arbitration_id
    assert bytes(frame.data) == bytes(msg.data)
    assert not hw.recv_frames(canbus_bus, 1, 0.3), "nothing should come back on the device side"


def test_bidirectional_burst(plc_bus: can.BusABC, canbus_bus: can.BusABC) -> None:
    sent_usb_to_device = []
    sent_device_to_usb = []
    for i in range(BURST_COUNT):
        a = can.Message(arbitration_id=0x100 + i, data=[i & 0xFF], is_extended_id=False)
        b = can.Message(arbitration_id=0x200 + i, data=[i & 0xFF], is_extended_id=False)
        plc_bus.send(a)
        canbus_bus.send(b)
        sent_usb_to_device.append(a)
        sent_device_to_usb.append(b)
        # Each SLCAN send is a full ASCII round-trip (frame + ack) over the serial link on both
        # ends -- a tiny pace between sends avoids overrunning either adapter's buffer at this rate.
        time.sleep(0.01)

    got_on_device = hw.recv_frames(canbus_bus, BURST_COUNT, 5.0)
    got_on_usb = hw.recv_frames(plc_bus, BURST_COUNT, 5.0)

    assert [f.arbitration_id for f in got_on_device] == [m.arbitration_id for m in sent_usb_to_device]
    assert [f.arbitration_id for f in got_on_usb] == [m.arbitration_id for m in sent_device_to_usb]


def test_usb_state_counters(plc, plc_bus: can.BusABC, canbus_bus: can.BusABC) -> None:
    """Secondary sanity check after the earlier tests in this module have already pushed traffic both
    ways -- counters are cumulative for the module-scoped bridge, so just check they moved, not exact values."""
    plc_bus.send(can.Message(arbitration_id=0x321, data=[9], is_extended_id=False))
    hw.recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
    canbus_bus.send(can.Message(arbitration_id=0x654, data=[8], is_extended_id=False))
    hw.recv_frames(plc_bus, 1, RX_TIMEOUT_S)

    state = plc.run_until("usb state", "app rx")
    assert "can bridge" in state, state
    # usb_bridge_cli.c's state format: "usb rx: N, tx: N, tx drops: N" / "device rx: N, rx drops: N, tx: N, ..."
    assert re.search(r"device rx: [1-9]\d*", state), state
    assert re.search(r"device rx: \d+, rx drops: \d+, tx: [1-9]\d*", state), state
    assert re.search(r"usb rx: [1-9]\d*", state), state
    assert re.search(r"usb rx: \d+, tx: [1-9]\d*", state), state
