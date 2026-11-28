"""HIL exhaustive frame-shape matrix for usb_bridge's CAN Bridge mode on BMPLC_XL (the production `usb can
bridge` CLI, pure pass-through -- see test_usb_bridge_can_bridge.py for the fixture/hardware-precondition
background, identical here). This file is purely about frame-shape correctness: standard vs extended ID,
data vs RTR, every DLC 0-8, and boundary ID values -- all at one fixed, representative bitrate (500000, the
suite's default and the firmware's own default when no baud is given to `usb can bridge`). Bitrate coverage
itself is test_usb_bridge_can_bridge_bitrates.py's job; multiplying this matrix across bitrates would add
~9x runtime for zero new information, since SLCAN's ASCII frame encoding doesn't change with bitrate.

Unlike the App-mode echo tests (test_usb_bridge_can_app.py), Bridge mode has no app callback at all
(usb_bridge_i.h's has_app() is false for UsbBridgeModeBridge), so there is no reserved control ID (App mode's
0x7FF triggers burst/periodic commands in the echo tool) and no id+1 echo arithmetic to work around -- every
frame is expected to cross unmodified, in either direction, including 0x7FF itself.
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


def _assert_data_frame_crossed(got, msg: "can.Message") -> None:
    assert got.arbitration_id == msg.arbitration_id
    assert got.is_extended_id == msg.is_extended_id
    assert not got.is_remote_frame
    assert got.dlc == msg.dlc
    assert bytes(got.data) == bytes(msg.data)


def _assert_rtr_crossed(got, msg: "can.Message") -> None:
    assert got.arbitration_id == msg.arbitration_id
    assert got.is_extended_id == msg.is_extended_id
    assert got.is_remote_frame
    assert got.dlc == msg.dlc


# ------------------------------------------------------------------ standard ID data frames, all DLCs


@pytest.mark.parametrize("dlc", range(9))
@pytest.mark.parametrize("can_id", [0x000, 0x001, 0x123, 0x7FE, 0x7FF])
def test_bridge_usb_to_device_std(plc_bus: can.BusABC, canbus_bus: can.BusABC, can_id: int, dlc: int) -> None:
    msg = can.Message(arbitration_id=can_id, data=bytes(range(dlc)), is_extended_id=False)
    plc_bus.send(msg)
    [got] = hw.recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
    _assert_data_frame_crossed(got, msg)
    assert not hw.recv_frames(plc_bus, 1, 0.3), "nothing should come back on the USB side"


@pytest.mark.parametrize("dlc", range(9))
@pytest.mark.parametrize("can_id", [0x000, 0x001, 0x123, 0x7FE, 0x7FF])
def test_bridge_device_to_usb_std(plc_bus: can.BusABC, canbus_bus: can.BusABC, can_id: int, dlc: int) -> None:
    msg = can.Message(arbitration_id=can_id, data=bytes(range(dlc)), is_extended_id=False)
    canbus_bus.send(msg)
    [got] = hw.recv_frames(plc_bus, 1, RX_TIMEOUT_S)
    _assert_data_frame_crossed(got, msg)
    assert not hw.recv_frames(canbus_bus, 1, 0.3), "nothing should come back on the device side"


# ------------------------------------------------------------------ extended ID data frames


@pytest.mark.parametrize("can_id", [0x00000000, 0x00000001, 0x00000800, 0x12345678, 0x1FFFFFFE, 0x1FFFFFFF])
def test_bridge_usb_to_device_ext(plc_bus: can.BusABC, canbus_bus: can.BusABC, can_id: int) -> None:
    msg = can.Message(arbitration_id=can_id, data=[1, 2, 3, 4], is_extended_id=True)
    plc_bus.send(msg)
    [got] = hw.recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
    _assert_data_frame_crossed(got, msg)
    assert not hw.recv_frames(plc_bus, 1, 0.3), "nothing should come back on the USB side"


@pytest.mark.parametrize("can_id", [0x00000000, 0x00000001, 0x00000800, 0x12345678, 0x1FFFFFFE, 0x1FFFFFFF])
def test_bridge_device_to_usb_ext(plc_bus: can.BusABC, canbus_bus: can.BusABC, can_id: int) -> None:
    msg = can.Message(arbitration_id=can_id, data=[5, 6, 7, 8], is_extended_id=True)
    canbus_bus.send(msg)
    [got] = hw.recv_frames(plc_bus, 1, RX_TIMEOUT_S)
    _assert_data_frame_crossed(got, msg)
    assert not hw.recv_frames(canbus_bus, 1, 0.3), "nothing should come back on the device side"


# ------------------------------------------------------------------ RTR (remote) frames


@pytest.mark.parametrize("dlc", [0, 1, 4, 7, 8])
@pytest.mark.parametrize("extended", [False, True])
def test_bridge_usb_to_device_rtr(plc_bus: can.BusABC, canbus_bus: can.BusABC, extended: bool, dlc: int) -> None:
    can_id = 0x1FFFFFFD if extended else 0x7FD
    msg = can.Message(arbitration_id=can_id, is_extended_id=extended, is_remote_frame=True, dlc=dlc)
    plc_bus.send(msg)
    [got] = hw.recv_frames(canbus_bus, 1, RX_TIMEOUT_S)
    _assert_rtr_crossed(got, msg)
    assert not hw.recv_frames(plc_bus, 1, 0.3), "nothing should come back on the USB side"


@pytest.mark.parametrize("dlc", [0, 1, 4, 7, 8])
@pytest.mark.parametrize("extended", [False, True])
def test_bridge_device_to_usb_rtr(plc_bus: can.BusABC, canbus_bus: can.BusABC, extended: bool, dlc: int) -> None:
    can_id = 0x1FFFFFFC if extended else 0x7FC
    msg = can.Message(arbitration_id=can_id, is_extended_id=extended, is_remote_frame=True, dlc=dlc)
    canbus_bus.send(msg)
    [got] = hw.recv_frames(plc_bus, 1, RX_TIMEOUT_S)
    _assert_rtr_crossed(got, msg)
    assert not hw.recv_frames(canbus_bus, 1, 0.3), "nothing should come back on the device side"
