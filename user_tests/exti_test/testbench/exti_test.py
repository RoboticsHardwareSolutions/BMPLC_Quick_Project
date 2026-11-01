"""HIL test for user_tests/exti_test/target/exti_test.c's `exti` RTT command.

io_test proves the bench can drive IN0-4 and the firmware's *polled* level read
(IN*_IS_HIGH) sees it. This module proves the hardware interrupt path itself:
the EXTI source routing (AFIO_EXTICR on F1 / SYSCFG_EXTICR on F7), the NVIC
vector enable and the EXTI line mask all have to be correct for a pin, or its
edges never reach the firmware's callback.

Per channel: `exti reset` -> bench asserts PLC_<T>_IN<n> (one rising edge) ->
channel n's counter must be exactly 1 and every other channel's exactly 0 ->
bench deasserts (one falling edge) -> channel n must be exactly 2, others still
0. A routing bug shows up as zero growth (or growth on the wrong channel); a
missing NVIC enable as zero growth everywhere.

Run against hardware with, e.g.:
    PLC_TYPE=BMPLC_M JLINK_SERIAL=000772440172 uv run pytest user_tests/exti_test/testbench/ -v

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
    COIL_SETTLE_S,
    DEFAULT_CONFIG_PATH,
    _pins_for,
    _TARGETS,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("PLC_TYPE"),
    reason="EXTI HIL tests require hardware: set PLC_TYPE=BMPLC_M|BMPLC_XL (see conftest.py)",
)


def _short_from_env() -> str:
    plc_type = os.environ.get("PLC_TYPE", "")
    if plc_type not in _TARGETS:
        pytest.fail(f"PLC_TYPE={plc_type!r} is not one of {sorted(_TARGETS)}")
    return _TARGETS[plc_type][1]


@functools.lru_cache(maxsize=None)
def _load_labels(config_path: str) -> testbench_client.TestbenchLabels:
    return testbench_client.TestbenchLabels.load(config_path)


# Collection-time pin derivation, same pattern as io_test.py: pytest.mark.parametrize's
# argument list is evaluated at collection time, before any fixture runs, so pin
# numbers can't come from the `tb_labels`/`io_config` fixtures -- re-derive them the
# same env-var/testbench.toml way, independently of fixtures.
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
    config_path = os.environ.get("TESTBENCH_CONFIG", str(DEFAULT_CONFIG_PATH))
    labels = _load_labels(config_path)
    pins = _pins_for(labels, short, "IN")
    metafunc.parametrize("n", pins, ids=[f"IN{p}" for p in pins])


def _assert_counts(plc, expected_for_n: int, n: int) -> None:
    counts = plc.read_exti_counts()
    assert counts.get(n) == expected_for_n, (
        f"channel {n} expected exactly {expected_for_n} edge(s), got: {counts}"
    )
    for other, count in counts.items():
        if other != n:
            assert count == 0, f"channel {other} leaked edge(s) while toggling channel {n}: {counts}"


def test_exti_edges(tb_client, tb_labels, plc, io_config, n):
    label = f"PLC_{io_config.short}_IN{n}"
    try:
        plc.run("exti reset")

        # Rising edge: bench asserts the input.
        mask, value = tb_labels.build_coil_request({label: True})
        tb_client.set_coils_mask(mask, value)
        time.sleep(COIL_SETTLE_S)
        _assert_counts(plc, 1, n)

        # Falling edge: bench deasserts the input.
        mask, value = tb_labels.build_coil_request({label: False})
        tb_client.set_coils_mask(mask, value)
        time.sleep(COIL_SETTLE_S)
        _assert_counts(plc, 2, n)
    finally:
        mask, value = tb_labels.build_coil_request({label: False})
        tb_client.set_coils_mask(mask, value)
