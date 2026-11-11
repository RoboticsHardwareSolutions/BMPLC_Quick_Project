"""Shared hardware access for the usb_bridge App mode host tests.

The board runs firmware with RHS_TEST_USB_BRIDGE_APP ON (target/usb_bridge_echo.c). The tests switch the echo
application between targets over RTT (`usb_bridge_echo can|rs232|stop|...`), so they need the J-Link too.

    USB_BRIDGE_PORT  USB CDC port of the board (on macOS /dev/cu.*, never /dev/tty.*), or `auto`: the
                     /dev/cu.usbmodem* that appears when the bridge starts

and either the HIL stand (power and USB of the PLC through the io_hub coils, see the root conftest.py)

    PLC_TYPE         BMPLC_M | BMPLC_XL, J-Link serial and MCU from testbench.toml; PLC_BIN flashes first

or a board on the desk

    JLINK_SERIAL     J-Link serial number
    MCU              J-Link device name, e.g. STM32G0B1KC

Without them every test is skipped. No VID/PID auto-detection: other firmware uses the same VID/PID.
"""

from __future__ import annotations

import glob
import os
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

PORT_SETTING = os.environ.get("USB_BRIDGE_PORT")
PLC_TYPE = os.environ.get("PLC_TYPE")
JLINK_SERIAL = os.environ.get("JLINK_SERIAL")
MCU = os.environ.get("MCU")

# Current port path, resolved by echo_start() when USB_BRIDGE_PORT=auto
PORT = None if PORT_SETTING == "auto" else PORT_SETTING

requires_rtt = pytest.mark.skipif(
    not (PLC_TYPE or (JLINK_SERIAL and MCU)),
    reason="usb_bridge tests need RTT: set PLC_TYPE (HIL stand) or JLINK_SERIAL and MCU",
)

requires_hw = pytest.mark.skipif(
    not (PORT_SETTING and (PLC_TYPE or (JLINK_SERIAL and MCU))),
    reason="usb_bridge App tests need a board with RHS_TEST_USB_BRIDGE_APP: set USB_BRIDGE_PORT and "
    "PLC_TYPE (HIL stand) or JLINK_SERIAL and MCU",
)

PORT_TIMEOUT_S = 8.0
STOP_TIMEOUT_S = 20.0  # stopping joins the USB and bridge threads
ENUMERATION_SETTLE_S = 0.5
AUTO_PATTERN = "/dev/cu.usbmodem*"


def _cdc_ports() -> set[str]:
    return set(glob.glob(AUTO_PATTERN))


def _wait(predicate, timeout: float, what: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise TimeoutError(f"{what} in {timeout} s")


def echo_start(rtt, target: str) -> None:
    global PORT
    before = _cdc_ports()
    out = rtt.run_until(f"usb_bridge_echo {target}", f"started {target}")
    assert f"started {target}" in out, out
    if PORT_SETTING == "auto":
        _wait(lambda: len(_cdc_ports() - before) == 1, PORT_TIMEOUT_S, f"no new {AUTO_PATTERN}")
        PORT = (_cdc_ports() - before).pop()
    else:
        _wait(lambda: os.path.exists(PORT), PORT_TIMEOUT_S, f"{PORT} did not appear")
    time.sleep(ENUMERATION_SETTLE_S)


def echo_stop(rtt) -> None:
    out = rtt.run_until("usb_bridge_echo stop", "stopped", timeout=STOP_TIMEOUT_S)
    assert "stopped" in out, out
    _wait(lambda: not os.path.exists(PORT), PORT_TIMEOUT_S, f"{PORT} did not disappear")
