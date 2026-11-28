"""HIL end-to-end test of usb_bridge, CAN target in Both/BridgeApp mode (`usb_bridge_echo can both`, which
registers the same echo callback as the App-mode tests while the physical bus is also bridged to USB).
Needs the HIL stand's [iface.canbus] adapter, same as test_usb_bridge_can_bridge.py, and BMPLC_XL only --
BMPLC_M rejects any CAN mode other than App.

Routing, confirmed by reading usb_bridge.c/usb_bridge_can.c/usb_bridge_i.h (deterministic, not a guess): the echo
callback's reply always targets UsbBridgePortUsb, regardless of which side the original frame came from.

  - A frame from the physical bus (canbus_bus) is forwarded unmodified to USB (pass-through, same as pure Bridge
    mode) AND separately echoed (id+1) back onto USB -- nothing extra ever reaches the device side.
  - A frame from USB (plc_bus) is forwarded unmodified to the device (pass-through) AND separately echoed (id+1)
    back onto USB -- the device side only ever sees the genuine forwarded frame, never the synthetic echo.

This has never been exercised on real hardware before (TODO.md: HIL Bridge tests "not written" at all) -- if the
pass-through half of these assertions breaks, test_usb_bridge_can_bridge.py's pure-Bridge test is the isolated
baseline to diff against.
"""

from __future__ import annotations

import os
from typing import Iterator

import pytest

import usb_bridge_hw as hw

can = pytest.importorskip("can")

pytestmark = pytest.mark.skipif(
    os.environ.get("PLC_TYPE") != "BMPLC_XL",
    reason="CAN Both E2E needs the HIL stand's [iface.canbus] adapter; BMPLC_XL only -- "
    "BMPLC_M rejects any CAN mode but App (see test_usb_bridge_cli.py)",
)

BITRATE = 500000
RX_TIMEOUT_S = 1.0


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
def echo_can_both(plc, io_config, request: pytest.FixtureRequest) -> Iterator[None]:
    hw.echo_start_can_both(plc, io_config, request)
    yield
    hw.echo_stop(plc, io_config, request)


@pytest.fixture
def plc_bus() -> Iterator[can.BusABC]:
    b = can.Bus(interface="slcan", channel=hw.PORT, bitrate=BITRATE, sleep_after_open=0.2)
    try:
        hw.recv_frames(b, 1000, 0.2)  # flush anything already queued
        yield b
    finally:
        b.shutdown()


def test_usb_originated_pass_through_and_echo(plc_bus: can.BusABC, canbus_bus: can.BusABC) -> None:
    msg = can.Message(arbitration_id=0x123, data=[1, 2, 3], is_extended_id=False)
    plc_bus.send(msg)

    [on_device] = hw.recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
    assert on_device.arbitration_id == msg.arbitration_id
    assert bytes(on_device.data) == bytes(msg.data)
    assert not hw.recv_frames(canbus_bus, 1, 0.3), "the echo must never reach the device side"

    [echo] = hw.recv_frames(plc_bus, 1, RX_TIMEOUT_S)
    assert echo.arbitration_id == msg.arbitration_id + 1
    assert bytes(echo.data) == bytes(msg.data)


def test_device_originated_pass_through_and_echo(plc_bus: can.BusABC, canbus_bus: can.BusABC) -> None:
    msg = can.Message(arbitration_id=0x456, data=[5, 6], is_extended_id=False)
    canbus_bus.send(msg)

    got = hw.recv_frames(plc_bus, 2, RX_TIMEOUT_S)
    assert len(got) == 2, got
    original, echo = got
    assert original.arbitration_id == msg.arbitration_id
    assert bytes(original.data) == bytes(msg.data)
    assert echo.arbitration_id == msg.arbitration_id + 1
    assert bytes(echo.data) == bytes(msg.data)

    assert not hw.recv_frames(canbus_bus, 1, 0.3), "nothing extra should come back to the device side"
