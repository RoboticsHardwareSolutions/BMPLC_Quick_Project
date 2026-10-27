"""HIL test for user_tests/io_test/target/io_test.c's `io` RTT command.

Pairs the bench's PLC_<T>_IN<n> (bench -> PLC) / PLC_<T>_OUT<n>/KEY<n> (PLC -> bench)
Modbus coils/bits with the firmware's `io key<n> on|off` / `io out<n> on|off` / bare
`io` RTT commands, in both directions:

- test_input:  bench asserts PLC_<T>_IN<n>  -> firmware's `io` reports IN<n> HIGH/LOW
- test_output: firmware's `io out<n>` drives a pin  -> bench reads PLC_<T>_OUT<n>
- test_key:    firmware's `io key<n>` drives a pin   -> bench reads PLC_<T>_KEY<n>

Run against hardware with, e.g.:
    PLC_TYPE=BMPLC_M JLINK_SERIAL=000772440172 uv run pytest user_tests/io_test/testbench/ -v

A plain `pytest` run with no `PLC_TYPE` set just skips this whole module (see
`pytestmark` below) -- nothing here touches the bench or a J-Link without it.
"""

from __future__ import annotations

import functools
import os
import time

import pytest

import testbench_client  # name kept off the module namespace: pytest would otherwise
# try to collect testbench_client.TestbenchLabels as a test class, since its name
# matches the default `Test*` python_classes pattern.
from conftest import (
    BIT_POLL_INTERVAL_S,
    BIT_POLL_TIMEOUT_S,
    COIL_SETTLE_S,
    DEFAULT_CONFIG_PATH,
    _pins_for,
    _TARGETS,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("PLC_TYPE"),
    reason="IO HIL tests require hardware: set PLC_TYPE=BMPLC_M|BMPLC_XL (see conftest.py)",
)


def _short_from_env() -> str:
    plc_type = os.environ.get("PLC_TYPE", "")
    if plc_type not in _TARGETS:
        pytest.fail(f"PLC_TYPE={plc_type!r} is not one of {sorted(_TARGETS)}")
    return _TARGETS[plc_type][1]


@functools.lru_cache(maxsize=None)
def _load_labels(config_path: str) -> testbench_client.TestbenchLabels:
    return testbench_client.TestbenchLabels.load(config_path)


# Collection-time pin derivation: pytest.mark.parametrize's argument list is evaluated
# at collection time, before any fixture runs, so pin numbers can't come from the
# `tb_labels`/`io_config` fixtures here -- this re-derives them the same
# env-var/testbench.toml way `io_config` does, independent of fixtures. Runs once per
# test function (test_input/test_output/test_key) that needs "n", so the cache above
# avoids reparsing the same toml three times during one collection pass.
def pytest_generate_tests(metafunc):
    if "n" not in metafunc.fixturenames:
        return

    # `pytestmark`'s skipif only takes effect at test-report time, which is *after*
    # this hook runs at collection time -- so a plain hardware-less `pytest` run (no
    # PLC_TYPE) must not fail here. Parametrize with one placeholder value instead and
    # let pytestmark produce the actual SKIPPED report.
    if not os.environ.get("PLC_TYPE"):
        metafunc.parametrize("n", [0], ids=["no-plc-type"])
        return

    short = _short_from_env()
    config_path = os.environ.get("IO_TEST_CONFIG", str(DEFAULT_CONFIG_PATH))
    labels = _load_labels(config_path)
    kind = {"test_input": "IN", "test_output": "OUT", "test_key": "KEY"}[metafunc.function.__name__]
    pins = _pins_for(labels, short, kind)
    metafunc.parametrize("n", pins, ids=[f"{kind}{p}" for p in pins])


def _wait_for_bit(tb_client, tb_labels, label: str, expected: bool) -> None:
    deadline = time.monotonic() + BIT_POLL_TIMEOUT_S
    last = None
    while time.monotonic() < deadline:
        bits = tb_client.get_inputs()["bits"]
        last = tb_labels.decode_inputs(bits)[label]
        if last == expected:
            return
        time.sleep(BIT_POLL_INTERVAL_S)
    pytest.fail(f"{label} did not reach {expected} within {BIT_POLL_TIMEOUT_S}s (last seen: {last})")


def test_input(tb_client, tb_labels, plc, io_config, n):
    label = f"PLC_{io_config.short}_IN{n}"
    try:
        mask, value = tb_labels.build_coil_request({label: True})
        tb_client.set_coils_mask(mask, value)
        time.sleep(COIL_SETTLE_S)
        assert plc.read_inputs().get(n) is True, f"PLC did not see {label}=HIGH via 'io'"

        mask, value = tb_labels.build_coil_request({label: False})
        tb_client.set_coils_mask(mask, value)
        time.sleep(COIL_SETTLE_S)
        assert plc.read_inputs().get(n) is False, f"PLC did not see {label}=LOW via 'io'"
    finally:
        mask, value = tb_labels.build_coil_request({label: False})
        tb_client.set_coils_mask(mask, value)


def test_output(tb_client, tb_labels, plc, io_config, n):
    label = f"PLC_{io_config.short}_OUT{n}"
    try:
        plc.set_out(n, True)
        _wait_for_bit(tb_client, tb_labels, label, True)
        plc.set_out(n, False)
        _wait_for_bit(tb_client, tb_labels, label, False)
    finally:
        plc.set_out(n, False)


def test_key(tb_client, tb_labels, plc, io_config, n):
    label = f"PLC_{io_config.short}_KEY{n}"
    try:
        plc.set_key(n, True)
        _wait_for_bit(tb_client, tb_labels, label, True)
        plc.set_key(n, False)
        _wait_for_bit(tb_client, tb_labels, label, False)
    finally:
        plc.set_key(n, False)
