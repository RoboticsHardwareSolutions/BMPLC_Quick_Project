"""CLI `usb` (usb_bridge service) over RTT: explicit errors for targets / modes the board does not support, start / state / stop,
one bridge at a time. Needs RTT only (no USB port), see usb_bridge_hw.py."""

from __future__ import annotations

import pytest

import usb_bridge_hw as hw

pytestmark = hw.requires_rtt

NO_ETH = "not supported on this board: no Ethernet"
NO_UART = "not supported on this board: no UART"
F103_CAN = "not supported on this board: CAN and USB share SRAM on STM32F103"

# command -> expected reason, per board (J-Link MCU name)
UNSUPPORTED = {
    "STM32G0B1KC": {
        "eth": ("eth bridge", NO_ETH),
        "ethernet app": ("eth app", NO_ETH),
        "rs232": ("rs232 bridge", NO_UART),
        "rs485 both": ("rs485 both", NO_UART),
    },
    "STM32F103RE": {
        "eth": ("eth bridge", NO_ETH),
        "can": ("can bridge", F103_CAN),
        "can both": ("can both", F103_CAN),
    },
    "STM32F765ZG": {},
}


def _cases():
    mcu = hw.MCU or {"BMPLC_M": "STM32F103RE", "BMPLC_XL": "STM32F765ZG"}.get(hw.PLC_TYPE or "", "")
    return sorted(UNSUPPORTED.get(mcu, {}).items())


@pytest.mark.parametrize(("args", "expected"), _cases() or [pytest.param(None, None, marks=pytest.mark.skip("all supported"))])
def test_unsupported_is_reported(rtt, args: str, expected: tuple[str, str]) -> None:
    what, reason = expected
    out = rtt.run_until(f"usb {args}", "error")
    assert f"error: {what}: {reason}" in out, out
    assert "stopped" in rtt.run_until("usb state", "stopped")


def test_unknown_target_and_mode(rtt) -> None:
    out = rtt.run_until("usb foo", "error")
    assert "error: unknown target 'foo'" in out, out
    out = rtt.run_until("usb can bogus", "error")
    assert "error: unknown mode 'bogus'" in out, out
    assert "stopped" in rtt.run_until("usb state", "stopped")


def test_start_state_stop_and_one_at_a_time(rtt) -> None:
    out = rtt.run_until("usb rs232 app 19200", "started")
    assert "started rs232 app" in out, out
    try:
        state = rtt.run_until("usb state", "app rx")
        assert "rs232 app" in state and "baudrate: 19200" in state, state
        out = rtt.run_until("usb_bridge_echo can", "error")
        assert "another bridge is running" in out, out
        out = rtt.run_until("usb can app", "error")
        assert "error: running, usb stop first" in out, out
    finally:
        assert "stopped" in rtt.run_until("usb stop", "stopped")
    assert "stopped" in rtt.run_until("usb state", "stopped")
