"""Root conftest: shared session fixtures for HIL (hardware-in-the-loop) tests.

Device-side testbench tests live in user_tests/<name>/testbench/*_test.py and
reuse these fixtures:

- io_config — resolved test configuration (PLC type, J-Link serial, MCU, toml path)
- testbench — connected IOController (Modbus RTU to the testbench hub)
- plc       — powered, optionally flashed and booted PLC (PlcRtt handle)

Configuration is passed via environment variables (io_test.py main() sets
them from its CLI arguments, which mirror the CI workflow matrix):

- PLC_TYPE        BMPLC_M | BMPLC_XL (required to run HIL tests)
- JLINK_SERIAL    J-Link serial, overrides [targets.*].jlink_serial from the toml
- MCU             bml MCU name, overrides [targets.*].mcu from the toml
- IO_TEST_CONFIG  path to testbench.toml (default: <repo>/testbench/testbench.toml)
- IO_TEST_BIN     path to bmplc.bin: flashed before the tests start
- IO_TEST_NO_POWER  set to "1" to not touch PWR/USB testbench coils

Nothing hardware-related happens at import/collection time: the testbench
modules are imported lazily inside fixtures, so a plain `pytest` run without
hardware only skips the HIL tests.
"""

import importlib.util
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent

# PLC types supported by the testbench wiring (testbench.toml labels).
PLC_TARGETS = {
    "BMPLC_M": {"target_key": "plc_m", "mcu": "STM32F103RE"},
    "BMPLC_XL": {"target_key": "plc_xl", "mcu": "STM32F765ZG"},
}

_PLACEHOLDER_SERIALS = {"", "..."}


@dataclass(frozen=True)
class IoConfig:
    plc_type: str
    target_key: str
    serial: str
    mcu: str
    config_path: Path
    bin_path: Path | None
    no_power: bool


def _load_module(name: str, path: Path):
    """Import a testbench module by file path (they are not a package)."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _resolve_io_config() -> IoConfig:
    plc_type = os.environ.get("PLC_TYPE", "").strip()
    if not plc_type:
        pytest.fail(
            "PLC_TYPE environment variable is not set. "
            "Run via io_test.py --plc-type ... or export PLC_TYPE."
        )
    if plc_type not in PLC_TARGETS:
        pytest.fail(f"Unsupported PLC_TYPE '{plc_type}'. Supported: {', '.join(sorted(PLC_TARGETS))}")

    target = PLC_TARGETS[plc_type]
    config_path = Path(os.environ.get("IO_TEST_CONFIG", REPO_ROOT / "testbench" / "testbench.toml"))
    if not config_path.is_file():
        pytest.fail(f"Testbench config not found: {config_path}")

    import tomllib

    with open(config_path, "rb") as f:
        toml = tomllib.load(f)

    target_cfg = toml.get("targets", {}).get(target["target_key"], {})

    serial = os.environ.get("JLINK_SERIAL", "").strip() or str(target_cfg.get("jlink_serial", "")).strip()
    if serial in _PLACEHOLDER_SERIALS:
        pytest.fail(
            f"J-Link serial for {plc_type} is not configured. Set JLINK_SERIAL or fill in "
            f"[targets.{target['target_key']}].jlink_serial in {config_path}"
        )

    mcu = os.environ.get("MCU", "").strip() or str(target_cfg.get("mcu", "")).strip() or target["mcu"]

    bin_env = os.environ.get("IO_TEST_BIN", "").strip()
    bin_path = Path(bin_env) if bin_env else None

    return IoConfig(
        plc_type=plc_type,
        target_key=target["target_key"],
        serial=serial,
        mcu=mcu,
        config_path=config_path,
        bin_path=bin_path,
        no_power=_env_flag("IO_TEST_NO_POWER"),
    )


@pytest.fixture(scope="session")
def io_config() -> IoConfig:
    return _resolve_io_config()


@pytest.fixture(scope="session")
def testbench(io_config: IoConfig):
    """Connected IOController (Modbus RTU to the testbench hub)."""
    modbus_io = _load_module("modbus_io", REPO_ROOT / "testbench" / "io.py")
    controller = modbus_io.IOController(config_path=str(io_config.config_path))
    if not controller.connect():
        pytest.fail(f"Failed to connect to testbench on {controller.conn['port']}")
    yield controller
    controller.close()


@pytest.fixture(scope="session")
def plc(io_config: IoConfig, testbench):
    """Powered (unless IO_TEST_NO_POWER), optionally flashed and booted PLC.

    Yields a PlcRtt handle. Teardown resets the board (init drives all
    OUT/KEY pins LOW) and powers it off.
    """
    rtt_mod = _load_module("plc_rtt", REPO_ROOT / "testbench" / "rtt.py")

    short = io_config.plc_type.split("_", 1)[1]  # BMPLC_M -> M
    pwr_label = f"PWR_PLC_{short}"
    usb_label = f"USB_PLC_{short}"

    if not io_config.no_power:
        results = testbench.write_outputs_by_labels([pwr_label, usb_label], True)
        if not all(results.values()):
            pytest.fail(f"Failed to power on {io_config.plc_type} via testbench: {results}")
        time.sleep(3.0)

    if io_config.bin_path is not None:
        rtt_mod.flash(str(io_config.bin_path), io_config.serial, io_config.mcu)

    rtt = rtt_mod.PlcRtt(io_config.serial, io_config.mcu)
    last_output = ""
    for _attempt in range(2):
        try:
            last_output = rtt.run("io", reset_board=True, timeout=30)
        except rtt_mod.BmlError as e:
            last_output = str(e)
        if "Input states:" in last_output:
            break
        time.sleep(2.0)
    else:
        pytest.fail(
            "PLC did not respond to the 'io' RTT command. Check that the board is powered, "
            f"the J-Link serial ({io_config.serial}) and MCU ({io_config.mcu}) are correct, "
            "and the firmware is a Debug build with RHS_TEST_IO enabled.\n"
            f"Last output:\n{last_output}"
        )

    yield rtt

    # Teardown: reset the board (init drives all OUT/KEY pins LOW), then power off.
    try:
        rtt.run("io", reset_board=True)
    except Exception as e:  # noqa: BLE001 - teardown must not mask the test result
        print(f"WARNING: failed to reset PLC during teardown: {e}")
    if not io_config.no_power:
        try:
            testbench.write_outputs_by_labels([pwr_label, usb_label], False)
        except Exception as e:  # noqa: BLE001 - teardown must not mask the test result
            print(f"WARNING: failed to power off {io_config.plc_type} during teardown: {e}")
