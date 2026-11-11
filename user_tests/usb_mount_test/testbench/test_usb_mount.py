"""USB mount callback of rhs_hal_usb (../target/usb_mount_test.c): `usb_mount` reports the state the callback saw.

    unit tests     `usb_mount_test` over RTT (TinyUSB callbacks driven by hand), RTT only
    start / stop   a usb_bridge (`usb can app`) brings the CDC device up: mounted once the host enumerates it,
                   `usb stop` reports unmounted. Needs the board's USB plugged into this host.
    cable          HIL stand only: the USB_PLC_<T> coil pulls the cable (seen as suspend), then plugs it back

The board runs firmware with RHS_TEST_USB_MOUNT ON. As for every test using `plc` (root conftest.py), either the HIL
stand (PLC_TYPE; its USB is on through the io_hub coil) or a board on the desk (JLINK_SERIAL and MCU). On the desk the
USB tests need USB_MOUNT_HOST=1 to say the board's USB is plugged into this host:

    JLINK_SERIAL=772440188 MCU=STM32G0B1KC USB_MOUNT_HOST=1 uv run pytest user_tests/usb_mount_test/testbench/ -v
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from conftest import hil_available  # noqa: E402
from testbench.pyhil.unit_tests import run_unit_test  # noqa: E402

STAND = bool(os.environ.get("PLC_TYPE"))
USB_HOST = STAND or os.environ.get("USB_MOUNT_HOST", "").strip().lower() in {"1", "true", "yes", "on"}

MOUNT_TIMEOUT_S = 8.0  # enumeration after the bridge starts or the cable is back
UMOUNT_TIMEOUT_S = 3.0  # suspend: bus idle for 3 ms, then the TinyUSB task
STOP_TIMEOUT_S = 20.0  # stopping joins the USB and bridge threads
POLL_S = 0.2

pytestmark = pytest.mark.skipif(
    not hil_available(),
    reason="usb_mount tests need RTT: set PLC_TYPE (HIL stand) or JLINK_SERIAL and MCU",
)

requires_usb_host = pytest.mark.skipif(
    not USB_HOST, reason="the board's USB must be plugged into this host: HIL stand or USB_MOUNT_HOST=1"
)

_STATE_RE = re.compile(r"mounted: (\d) mount: (\d+) umount: (\d+)")


def mount_state(plc) -> tuple[bool, int, int]:
    out = plc.run_until("usb_mount", "umount")
    m = _STATE_RE.search(out)
    assert m, out
    return m.group(1) == "1", int(m.group(2)), int(m.group(3))


def wait_mounted(plc, mounted: bool, timeout: float) -> tuple[bool, int, int]:
    deadline = time.monotonic() + timeout
    state = mount_state(plc)
    while state[0] != mounted and time.monotonic() < deadline:
        time.sleep(POLL_S)
        state = mount_state(plc)
    assert state[0] == mounted, f"mounted={state[0]} after {timeout} s, expected {mounted}: {state}"
    return state


def bridge_start(plc) -> None:
    out = plc.run_until("usb can app", "started")
    assert "started can app" in out, out


def bridge_stop(plc) -> None:
    out = plc.run_until("usb stop", "stopped", timeout=STOP_TIMEOUT_S)
    assert "stopped" in out, out


def bridge_ensure_stopped(plc) -> None:
    # `usb stop` prints nothing when no bridge runs
    if "stopped" not in plc.run_until("usb state", "stopped"):
        bridge_stop(plc)


@pytest.fixture
def no_bridge(plc):
    """No USB interface before and after the test: unmounted, counters at zero."""
    bridge_ensure_stopped(plc)
    assert "reset" in plc.run_until("usb_mount reset", "reset")
    yield
    bridge_ensure_stopped(plc)


def test_unit(plc, no_bridge) -> None:
    report = run_unit_test(plc, "usb_mount_test")
    assert report.ok, report.raw
    assert "skipped" not in report.raw, report.raw
    assert report.passes, report.raw


def test_unmounted_without_interface(plc, no_bridge) -> None:
    assert mount_state(plc) == (False, 0, 0)


@requires_usb_host
def test_bridge_start_stop(plc, no_bridge) -> None:
    bridge_start(plc)
    mounted, mount, umount = wait_mounted(plc, True, MOUNT_TIMEOUT_S)
    assert (mount, umount) == (1, 0)

    bridge_stop(plc)
    mounted, mount, umount = mount_state(plc)
    assert not mounted
    assert (mount, umount) == (1, 1)

    # Again: one more pair of events, no stale state from the previous interface
    bridge_start(plc)
    wait_mounted(plc, True, MOUNT_TIMEOUT_S)
    bridge_stop(plc)
    assert mount_state(plc) == (False, 2, 2)


@pytest.mark.skipif(not STAND, reason="pulling the USB cable needs the HIL stand (USB_PLC_<T> coil)")
def test_cable_pull(plc, no_bridge, io_config, tb_client, tb_labels) -> None:
    usb_coil = f"USB_PLC_{io_config.short}"

    def usb_cable(on: bool) -> None:
        mask, value = tb_labels.build_coil_request({usb_coil: on})
        tb_client.set_coils_mask(mask, value)

    bridge_start(plc)
    wait_mounted(plc, True, MOUNT_TIMEOUT_S)
    try:
        usb_cable(False)
        _, mount, umount = wait_mounted(plc, False, UMOUNT_TIMEOUT_S)
        assert (mount, umount) == (1, 1)

        usb_cable(True)
        _, mount, umount = wait_mounted(plc, True, MOUNT_TIMEOUT_S)
        assert (mount, umount) == (2, 1)
    finally:
        usb_cable(True)
