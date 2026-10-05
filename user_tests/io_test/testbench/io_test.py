"""HIL tests for PLC IO (IN/OUT/KEY lines) driven through the testbench.

The testbench hub is controlled over Modbus RTU (testbench/io.py) and the
PLC over its RTT CLI `io` command (bml rtt, see testbench/rtt.py):

- IN<n>  — the testbench drives coil PLC_<T>_IN<n>, the PLC must read it HIGH/LOW
- OUT<n> — the PLC drives the pin via `io out<n> on|off`, the testbench reads bit PLC_<T>_OUT<n>
- KEY<n> — the same for `io key<n>` and bit PLC_<T>_KEY<n>

Pin lists are derived from the labels in testbench.toml (PLC_<T>_IN<n>,
PLC_<T>_OUT<n>, PLC_<T>_KEY<n>), so new wiring added to the config is
covered automatically.

Usage (matrix-compatible CLI, same arguments as the CI workflow):
    python user_tests/io_test/testbench/io_test.py --plc-type BMPLC_M \
        [--jlink-serial S] [--mcu M] [--config PATH] [--bin build_m/bmplc.bin] \
        [--no-power] [extra pytest args...]

Or plain pytest with environment variables:
    PLC_TYPE=BMPLC_M JLINK_SERIAL=S pytest user_tests/io_test/testbench/ -v
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTBENCH_DIR = REPO_ROOT / "testbench"

# Settle time after a testbench coil write before reading the PLC state.
COIL_SETTLE_S = 0.3
# Polling window for testbench input bits after an RTT command.
BIT_POLL_TIMEOUT_S = 2.0
BIT_POLL_INTERVAL_S = 0.15


def _load_toml() -> dict:
    import tomllib

    config_path = Path(os.environ.get("IO_TEST_CONFIG", TESTBENCH_DIR / "testbench.toml"))
    if not config_path.is_file():
        raise FileNotFoundError(f"Testbench config not found: {config_path}")
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def _plc_short() -> str:
    """BMPLC_M -> M, BMPLC_XL -> XL (the suffix used in testbench labels)."""
    plc_type = os.environ.get("PLC_TYPE", "")
    return plc_type.split("_", 1)[1] if "_" in plc_type else ""


def _pins_for(kind: str) -> list[int]:
    """Pin indices for PLC_<T>_<kind><n> labels in the testbench config.

    kind "IN" — testbench-driven coils ([io.map.outputs].labels);
    kind "OUT"/"KEY" — PLC-driven bits read by the testbench ([io.map.inputs].labels).
    """
    toml = _load_toml()
    maps = toml.get("io", {}).get("map", {})
    if kind == "IN":
        labels = list(maps.get("outputs", {}).get("labels", {}).values())
    else:
        labels = list(maps.get("inputs", {}).get("labels", {}).values())

    pattern = re.compile(rf"^PLC_{re.escape(_plc_short())}_{kind}(\d+)$")
    return sorted({int(m.group(1)) for label in labels if (m := pattern.match(label))})


pytestmark = pytest.mark.skipif(
    not os.environ.get("PLC_TYPE"),
    reason="IO HIL tests: run via io_test.py --plc-type ... or set the PLC_TYPE environment variable",
)


def _wait_for_bit(testbench, label: str, expected: bool) -> None:
    """Poll the testbench input bit until it matches (or the window expires)."""
    deadline = time.monotonic() + BIT_POLL_TIMEOUT_S
    last = None
    while True:
        states = testbench.read_inputs()
        assert states is not None, f"Failed to read testbench inputs while waiting for {label}"
        last = states.get(label)
        if last == expected:
            return
        if time.monotonic() >= deadline:
            break
        time.sleep(BIT_POLL_INTERVAL_S)
    pytest.fail(f"Testbench bit {label} is {last}, expected {expected}")


def _read_plc_input_until(plc, n: int, expected: bool) -> None:
    """Read IN<n> from the PLC via RTT; retry once after a settle delay."""
    states = plc.read_inputs()
    if n not in states:
        pytest.fail(f"PLC 'io' output does not contain IN{n}: {states}")
    if states[n] == expected:
        return
    time.sleep(COIL_SETTLE_S)
    states = plc.read_inputs()
    assert n in states, f"PLC 'io' output does not contain IN{n}: {states}"
    assert states[n] == expected, (
        f"PLC did not read IN{n} as {'HIGH' if expected else 'LOW'} (last states={states})"
    )


@pytest.mark.parametrize("n", _pins_for("IN"), ids=lambda n: f"IN{n}")
def test_input(testbench, plc, n):
    """Testbench drives PLC_<T>_IN<n>; the PLC must see it via RTT `io`."""
    label = f"PLC_{_plc_short()}_IN{n}"
    try:
        assert testbench.write_output_by_label(label, True), f"Failed to set coil {label}"
        time.sleep(COIL_SETTLE_S)
        _read_plc_input_until(plc, n, True)

        assert testbench.write_output_by_label(label, False), f"Failed to clear coil {label}"
        time.sleep(COIL_SETTLE_S)
        _read_plc_input_until(plc, n, False)
    finally:
        try:
            testbench.write_output_by_label(label, False)
        except Exception:  # noqa: BLE001 - teardown must not mask the test result
            pass


@pytest.mark.parametrize("n", _pins_for("OUT"), ids=lambda n: f"OUT{n}")
def test_output(testbench, plc, n):
    """PLC drives OUT<n> via RTT; the testbench must see PLC_<T>_OUT<n>."""
    label = f"PLC_{_plc_short()}_OUT{n}"
    try:
        plc.set_out(n, True)
        _wait_for_bit(testbench, label, True)

        plc.set_out(n, False)
        _wait_for_bit(testbench, label, False)
    finally:
        try:
            plc.set_out(n, False)
        except Exception:  # noqa: BLE001 - teardown must not mask the test result
            pass


@pytest.mark.parametrize("n", _pins_for("KEY"), ids=lambda n: f"KEY{n}")
def test_key(testbench, plc, n):
    """PLC drives KEY<n> via RTT; the testbench must see PLC_<T>_KEY<n>."""
    label = f"PLC_{_plc_short()}_KEY{n}"
    try:
        plc.set_key(n, True)
        _wait_for_bit(testbench, label, True)

        plc.set_key(n, False)
        _wait_for_bit(testbench, label, False)
    finally:
        try:
            plc.set_key(n, False)
        except Exception:  # noqa: BLE001 - teardown must not mask the test result
            pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="IO HIL tests for BMPLC boards (pytest). "
        "Arguments mirror the CI workflow matrix.",
    )
    parser.add_argument("--plc-type", required=True, choices=["BMPLC_M", "BMPLC_XL"],
                        help="PLC type under test")
    parser.add_argument("--jlink-serial", default=None,
                        help="J-Link serial (default: from testbench.toml [targets])")
    parser.add_argument("--mcu", default=None,
                        help="MCU name for bml (default: from testbench.toml [targets])")
    parser.add_argument("--config", default=None,
                        help="Path to testbench.toml (default: <repo>/testbench/testbench.toml)")
    parser.add_argument("--bin", default=None,
                        help="Path to bmplc.bin: flash it before running the tests")
    parser.add_argument("--no-power", action="store_true",
                        help="Do not touch PWR/USB testbench coils (board already powered)")
    args, extra_pytest_args = parser.parse_known_args()

    os.environ["PLC_TYPE"] = args.plc_type
    if args.jlink_serial:
        os.environ["JLINK_SERIAL"] = args.jlink_serial
    if args.mcu:
        os.environ["MCU"] = args.mcu
    if args.config:
        os.environ["IO_TEST_CONFIG"] = str(Path(args.config).resolve())
    if args.bin:
        os.environ["IO_TEST_BIN"] = str(Path(args.bin).resolve())
    if args.no_power:
        os.environ["IO_TEST_NO_POWER"] = "1"

    return pytest.main([str(Path(__file__).resolve()), "-v", "--tb=short"] + extra_pytest_args)


if __name__ == "__main__":
    sys.exit(main())
