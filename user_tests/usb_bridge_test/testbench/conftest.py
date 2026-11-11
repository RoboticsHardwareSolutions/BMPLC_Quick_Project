"""Fixtures of the usb_bridge host tests, see usb_bridge_hw.py."""

from __future__ import annotations

import time
from typing import Iterator

import pytest

import usb_bridge_hw as hw

RTT_BOOT_SETTLE_S = 2.0
RTT_READY_RETRIES = 5
RTT_READY_TIMEOUT_S = 5.0
RTT_QUIET_S = 1.0


@pytest.fixture(scope="module")
def rtt(request) -> Iterator["PlcRtt"]:
    from bmlab_toolkit import JLinkProgrammer

    from testbench.pyhil.rtt import PlcRtt

    if hw.PLC_TYPE:
        # HIL stand: the root conftest powers the PLC and enables its USB for this module
        io_config = request.getfixturevalue("io_config")
        request.getfixturevalue("plc_power")
        serial, mcu, bin_path = io_config.serial, io_config.mcu, io_config.bin_path
    else:
        serial, mcu, bin_path = int(hw.JLINK_SERIAL), hw.MCU, None

    programmer = JLinkProgrammer(serial=serial)
    try:
        if bin_path is not None:
            assert programmer.flash(str(bin_path), mcu=mcu), f"flashing {bin_path} failed"
        assert programmer.start_rtt(mcu=mcu, reset=True), "RTT did not start"
        time.sleep(RTT_BOOT_SETTLE_S)
        rtt = PlcRtt(programmer)
        rtt.mcu = mcu  # board-specific expectations in the tests
        # Boot log first (XL boots its network for a while): wait until the CLI answers
        for _ in range(RTT_READY_RETRIES):
            if "Available commands" in rtt.run_until("?", "Available commands", timeout=RTT_READY_TIMEOUT_S):
                break
        else:
            pytest.fail("CLI does not answer '?' over RTT")
        time.sleep(RTT_QUIET_S)
        rtt.run("")  # drop late boot log lines
        yield rtt
    finally:
        programmer.stop_rtt()
        programmer.disconnect_target()
