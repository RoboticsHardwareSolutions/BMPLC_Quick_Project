"""Shared hardware access for the usb_bridge host tests (App, Bridge, Both/BridgeApp).

The board runs firmware with RHS_TEST_USB_BRIDGE_APP ON (target/usb_bridge_echo.c) for App/Both-mode tests, or is
driven directly through the production `usb` CLI (thirdparty/rhs/applications/services/usb_bridge/usb_bridge_cli.c)
for pure Bridge-mode tests. Either way the tests exchange RTT commands through the root conftest's `plc` fixture,
so they need the J-Link too.

On the HIL stand (PLC_TYPE set), the PLC's own CDC port is resolved deterministically by `usb_location`
(testbench.toml's `[targets.<key>].usb_location`, an IOKit locationID) via the io_hub daemon's
TB_OP_RESOLVE_USB_LOCATION, exactly like the bench's own `[iface.*]` adapters are resolved -- see
`plc_cdc_port()`/`canbus_port()` below. There is deliberately no before/after USB-device-list diffing: it's
racy against stale nodes from a crashed prior session and gives no story for telling "still enumerating" apart
from "never came up". A board on the desk (JLINK_SERIAL+MCU, no io_hub) has no usb_location to resolve against,
so `USB_BRIDGE_PORT` must be given as an explicit literal /dev path there.

    USB_BRIDGE_PORT  explicit /dev/cu.* path -- desk mode only (see above); ignored on the HIL stand

and, as for every test using `plc` (root conftest.py), either the HIL stand (power and USB of the PLC through the
io_hub coils)

    PLC_TYPE         BMPLC_M | BMPLC_XL, J-Link serial and MCU from testbench.toml; PLC_BIN flashes first

or a board on the desk

    JLINK_SERIAL     J-Link serial number
    MCU              J-Link device name, e.g. STM32G0B1KC

Without them every test is skipped. No VID/PID auto-detection: other firmware uses the same VID/PID.
"""

from __future__ import annotations

import os
import sys
import time
import tomllib
from pathlib import Path
from typing import Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "testbench" / "io_hub" / "client" / "python"))

from conftest import DEFAULT_CONFIG_PATH, hil_available  # noqa: E402
from testbench_client import TB_IFACE_CANBUS, TestbenchClient  # noqa: E402

PORT_SETTING = os.environ.get("USB_BRIDGE_PORT")  # desk mode only, see module docstring
PLC_TYPE = os.environ.get("PLC_TYPE")
MCU = os.environ.get("MCU")
TESTBENCH_CONFIG = Path(os.environ.get("TESTBENCH_CONFIG", DEFAULT_CONFIG_PATH))

_TARGET_KEYS = {"BMPLC_M": "plc_m", "BMPLC_XL": "plc_xl"}

# Current PLC CDC port path -- resolved by _start_and_discover_port() on the stand (usb_location) or taken
# verbatim from USB_BRIDGE_PORT on the desk.
PORT = PORT_SETTING


def _configured_usb_location() -> int:
    """PLC_TYPE's own [targets.<key>].usb_location from testbench.toml, or 0 if PLC_TYPE isn't a stand
    target or the config doesn't have it filled in yet. Only used for the requires_hw gate at collection
    time -- desk mode (JLINK_SERIAL+MCU) has no usb_location concept at all, it relies on USB_BRIDGE_PORT."""
    target_key = _TARGET_KEYS.get(PLC_TYPE or "")
    if not target_key:
        return 0
    try:
        with open(TESTBENCH_CONFIG, "rb") as f:
            toml = tomllib.load(f)
    except OSError:
        return 0
    return int(toml.get("targets", {}).get(target_key, {}).get("usb_location", 0) or 0)


def _target_usb_location(io_config) -> int:
    """io_config's own usb_location, read straight from testbench.toml -- raises if the HIL stand's
    config doesn't have [targets.<key>].usb_location filled in (see testbench.toml's TODO placeholders)."""
    target_key = io_config.target_key
    with open(io_config.config_path, "rb") as f:
        toml = tomllib.load(f)
    location = toml.get("targets", {}).get(target_key, {}).get("usb_location")
    if not location:
        raise RuntimeError(
            f"testbench.toml's [targets.{target_key}] has no usb_location set -- measure it on the stand "
            "(ioreg -p IOUSB -l | grep -i locationID) and fill it in"
        )
    return int(location)


requires_rtt = pytest.mark.skipif(
    not hil_available(),
    reason="usb_bridge tests need RTT: set PLC_TYPE (HIL stand) or JLINK_SERIAL and MCU",
)

requires_hw = pytest.mark.skipif(
    not ((PORT_SETTING or _configured_usb_location()) and hil_available()),
    reason="usb_bridge App tests need a board with RHS_TEST_USB_BRIDGE_APP: on the HIL stand set PLC_TYPE with "
    "[targets.<key>].usb_location filled in testbench.toml; on the desk set USB_BRIDGE_PORT and "
    "JLINK_SERIAL+MCU",
)

PORT_TIMEOUT_S = 8.0
STOP_TIMEOUT_S = 20.0  # stopping joins the USB and bridge threads
ENUMERATION_SETTLE_S = 0.5


def _wait(predicate, timeout: float, what: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise TimeoutError(f"{what} in {timeout} s")


def plc_cdc_port(tb_client: TestbenchClient, usb_location: int, timeout: float = PORT_TIMEOUT_S) -> str:
    """Poll the daemon's TB_OP_RESOLVE_USB_LOCATION until the PLC's own CDC port enumerates at
    `usb_location` (set by whichever bridge just started) -- the stand-side replacement for
    diffing /dev/cu.usbmodem* snapshots."""
    resolved: dict[str, str] = {}

    def _check() -> bool:
        path = tb_client.resolve_usb_location(usb_location)
        if path is None:
            return False
        resolved["path"] = path
        return True

    _wait(_check, timeout, f"no device at usb_location 0x{usb_location:x}")
    return resolved["path"]


def _wait_port_gone(tb_client: TestbenchClient, usb_location: int, timeout: float = PORT_TIMEOUT_S) -> None:
    _wait(
        lambda: tb_client.resolve_usb_location(usb_location) is None,
        timeout,
        f"usb_location 0x{usb_location:x} did not disappear",
    )


def _start_and_discover_port(plc, io_config, request: pytest.FixtureRequest, start_cmd: str, started_marker: str) -> None:
    """Run `start_cmd` over RTT, assert it reports `started_marker`, then resolve the PLC's own CDC port:
    via usb_location on the HIL stand, or wait for the literal USB_BRIDGE_PORT path to appear on the desk."""
    global PORT
    out = plc.run_until(start_cmd, started_marker)
    assert started_marker in out, out
    if io_config.stand:
        tb_client = request.getfixturevalue("tb_client")
        PORT = plc_cdc_port(tb_client, _target_usb_location(io_config))
    else:
        assert PORT_SETTING, "desk mode needs an explicit USB_BRIDGE_PORT (no usb_location on the desk)"
        _wait(lambda: os.path.exists(PORT), PORT_TIMEOUT_S, f"{PORT} did not appear")
    time.sleep(ENUMERATION_SETTLE_S)


def _stop_and_wait_port_gone(plc, io_config, request: pytest.FixtureRequest, stop_cmd: str) -> None:
    out = plc.run_until(stop_cmd, "stopped", timeout=STOP_TIMEOUT_S)
    assert "stopped" in out, out
    if io_config.stand:
        tb_client = request.getfixturevalue("tb_client")
        _wait_port_gone(tb_client, _target_usb_location(io_config))
    else:
        _wait(lambda: not os.path.exists(PORT), PORT_TIMEOUT_S, f"{PORT} did not disappear")


def echo_start(plc, target: str, io_config, request: pytest.FixtureRequest) -> None:
    _start_and_discover_port(plc, io_config, request, f"usb_bridge_echo {target}", f"started {target}")


def echo_stop(plc, io_config, request: pytest.FixtureRequest) -> None:
    _stop_and_wait_port_gone(plc, io_config, request, "usb_bridge_echo stop")


def echo_start_can_both(plc, io_config, request: pytest.FixtureRequest) -> None:
    _start_and_discover_port(plc, io_config, request, "usb_bridge_echo can both", "started can both")


def bridge_start(plc, mode: str, io_config, request: pytest.FixtureRequest, baud: int | None = None) -> None:
    """Start the **production** `usb can {mode}` CLI bridge (not the usb_bridge_echo test tool)."""
    cmd = f"usb can {mode}" + (f" {baud}" if baud else "")
    _start_and_discover_port(plc, io_config, request, cmd, f"started can {mode}")


def bridge_stop(plc, io_config, request: pytest.FixtureRequest) -> None:
    _stop_and_wait_port_gone(plc, io_config, request, "usb stop")


def canbus_port(tb_client: TestbenchClient) -> str | None:
    """The bench's [iface.canbus] adapter path (a CANable 2.0, slcan/Lawicel-style over a USB-CDC virtual
    COM port -- see testbench/testbench.toml's [iface.canbus]), or None if it's not currently detected."""
    present, path = tb_client.iface_available(TB_IFACE_CANBUS)
    return path if present else None


def recv_frames(bus, count: int, timeout: float) -> list:
    """Collect up to `count` CAN frames from `bus` within `timeout` seconds (python-can Bus)."""
    frames = []
    deadline = time.monotonic() + timeout
    while len(frames) < count and time.monotonic() < deadline:
        msg = bus.recv(0.1)
        if msg is not None:
            frames.append(msg)
    return frames
