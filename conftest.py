"""Root pytest fixtures for the BMPLC HIL test suite (user_tests/<name>/testbench/).

Enforces the safety ordering the HIL rig needs:

    io_hub_daemon -> tb_client -> plc_power -> plc

i.e. the io_hub daemon (which alone can hold the stand's RS485 link) must be up
before any coil is read/written, and a PLC's power+USB-enable coils must be asserted
before flashing/connecting RTT to it. Teardown runs in the exact reverse order via
pytest's own yield-fixture finalizer stack, which fires even if a test or another
fixture's setup raised -- no fixture here needs a manual try/except around its own
cleanup.

Every HIL test module should set `pytestmark = pytest.mark.skipif(not
os.environ.get("PLC_TYPE"), ...)` so a plain `pytest` run with no hardware attached
just skips instead of touching anything.
"""

from __future__ import annotations

import os
import re
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pytest
from bmlab_toolkit import JLinkProgrammer

REPO_ROOT = Path(__file__).resolve().parent

sys.path.insert(0, str(REPO_ROOT / "testbench" / "io_hub" / "client" / "python"))
from testbench_client import TestbenchClient, TestbenchLabels  # noqa: E402

sys.path.insert(0, str(REPO_ROOT))
from testbench.pyhil.daemon import IoHubDaemon, resolve_daemon_binary  # noqa: E402
from testbench.pyhil.rtt import PlcRtt  # noqa: E402

DEFAULT_CONFIG_PATH = REPO_ROOT / "testbench" / "testbench.toml"

# --- Timing constants (placeholders ported from the pre-rewrite HIL framework; not
# re-tuned against this IPC-based rewrite on real hardware -- adjust after a first
# real run if they prove too tight/loose). Centralized here since both this file and
# user_tests/*/testbench/*.py need them. ---
PLC_BOOT_SETTLE_S = 3.0  # after asserting PWR_PLC_<T>/USB_PLC_<T>, before flashing/RTT
COIL_SETTLE_S = 0.3  # after writing a bench-driven input coil, before reading the PLC
BIT_POLL_TIMEOUT_S = 2.0  # waiting for a bench-read input bit to reflect a PLC-driven OUT/KEY
BIT_POLL_INTERVAL_S = 0.15
RTT_READY_RETRIES = 3
RTT_READY_TIMEOUT_S = 10.0
RTT_READY_RETRY_DELAY_S = 2.0

_PLACEHOLDER_SERIALS = {"", "..."}

_TARGETS = {
    "BMPLC_M": ("plc_m", "M"),
    "BMPLC_XL": ("plc_xl", "XL"),
}


@dataclass(frozen=True)
class IoConfig:
    plc_type: str  # "BMPLC_M" | "BMPLC_XL"
    target_key: str  # "plc_m" | "plc_xl" -- key into testbench.toml [targets.*]
    short: str  # "M" | "XL" -- label suffix, e.g. PLC_<short>_IN0
    serial: int  # J-Link serial number
    mcu: str
    config_path: Path
    bin_path: Path | None
    no_power: bool


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _pins_for(labels: TestbenchLabels, short: str, kind: str) -> list[int]:
    """PLC_<short>_<kind><n> label names -> sorted list of n.

    `kind` is "IN" (bench-driven, in labels.output_addr) or "OUT"/"KEY" (bench-read,
    in labels.input_bit). Deriving pins from testbench.toml rather than hardcoding
    range(5) means new wiring is picked up automatically -- shared between this
    file's own `plc` fixture teardown and user_tests/*/testbench/*.py's collection-time
    parametrization.
    """
    source = labels.output_addr if kind == "IN" else labels.input_bit
    pattern = re.compile(rf"^PLC_{re.escape(short)}_{kind}(\d+)$")
    pins = set()
    for name in source:
        m = pattern.match(name)
        if m:
            pins.add(int(m.group(1)))
    return sorted(pins)


@pytest.fixture(scope="session")
def io_config() -> IoConfig:
    plc_type = os.environ.get("PLC_TYPE")
    if not plc_type:
        pytest.fail(
            "PLC_TYPE is not set. HIL tests need hardware: set PLC_TYPE=BMPLC_M or "
            "BMPLC_XL (and usually JLINK_SERIAL) before running pytest."
        )
    if plc_type not in _TARGETS:
        pytest.fail(f"PLC_TYPE={plc_type!r} is not one of {sorted(_TARGETS)}")
    target_key, short = _TARGETS[plc_type]

    config_path = Path(os.environ.get("IO_TEST_CONFIG", DEFAULT_CONFIG_PATH))
    with open(config_path, "rb") as f:
        toml = tomllib.load(f)
    target = toml.get("targets", {}).get(target_key, {})

    serial_str = os.environ.get("JLINK_SERIAL") or str(target.get("jlink_serial", ""))
    if serial_str in _PLACEHOLDER_SERIALS:
        pytest.fail(
            f"no usable J-Link serial for {target_key}: set JLINK_SERIAL, or fill in "
            f"testbench.toml's [targets.{target_key}].jlink_serial (currently {serial_str!r})"
        )
    try:
        serial = int(serial_str, 10)
    except ValueError:
        pytest.fail(f"JLINK_SERIAL/[targets.{target_key}].jlink_serial={serial_str!r} is not an integer")

    mcu = os.environ.get("MCU") or target.get("mcu")
    if not mcu:
        pytest.fail(f"no MCU name for {target_key}: set MCU, or fill in testbench.toml's [targets.{target_key}].mcu")

    bin_env = os.environ.get("IO_TEST_BIN")
    bin_path = Path(bin_env) if bin_env else None

    return IoConfig(
        plc_type=plc_type,
        target_key=target_key,
        short=short,
        serial=serial,
        mcu=mcu,
        config_path=config_path,
        bin_path=bin_path,
        no_power=_env_truthy("IO_TEST_NO_POWER"),
    )


@pytest.fixture(scope="session")
def io_hub_daemon(io_config: IoConfig) -> Iterator[IoHubDaemon | None]:
    # A daemon may already be running from a prior session (e.g. one that crashed
    # before teardown); ping() is the one call documented to never raise, so it's the
    # correct probe for "is anything actually answering" as opposed to "does a stale
    # socket file exist." Reuse it rather than spawning a second instance, since only
    # one process may ever hold the stand's serial port at a time. Only resolve/spawn
    # a binary when we actually need one -- a reused daemon shouldn't require a local
    # build artifact to exist.
    already_up = _ping_once()

    daemon = None
    if not already_up:
        daemon = IoHubDaemon(resolve_daemon_binary(), io_config.config_path)
        daemon.start(ping=_ping_once)
    try:
        yield daemon
    finally:
        if daemon is not None:
            daemon.stop()


def _ping_once() -> bool:
    client = TestbenchClient()
    try:
        return client.ping()
    finally:
        client.close()


@pytest.fixture(scope="session")
def tb_client(io_hub_daemon: IoHubDaemon) -> Iterator[TestbenchClient]:
    client = TestbenchClient()
    assert client.ping(), "testbench daemon did not come up on the IPC socket"
    yield client
    client.close()


@pytest.fixture(scope="session")
def tb_labels(io_config: IoConfig) -> TestbenchLabels:
    return TestbenchLabels.load(io_config.config_path)


@pytest.fixture(scope="module")
def plc_power(io_config: IoConfig, tb_client: TestbenchClient, tb_labels: TestbenchLabels) -> Iterator[None]:
    pwr, usb = f"PWR_PLC_{io_config.short}", f"USB_PLC_{io_config.short}"

    if not io_config.no_power:
        mask, value = tb_labels.build_coil_request({pwr: True, usb: True})
        tb_client.set_coils_mask(mask, value)
        time.sleep(PLC_BOOT_SETTLE_S)

    try:
        yield
    finally:
        if not io_config.no_power:
            mask, value = tb_labels.build_coil_request({pwr: False, usb: False})
            tb_client.set_coils_mask(mask, value)


@pytest.fixture(scope="module")
def plc(io_config: IoConfig, plc_power: None, tb_labels: TestbenchLabels) -> Iterator[PlcRtt]:
    programmer = JLinkProgrammer(serial=io_config.serial)

    try:
        if io_config.bin_path is not None:
            assert programmer.flash(str(io_config.bin_path), mcu=io_config.mcu), (
                f"flashing {io_config.bin_path} to {io_config.mcu} (serial {io_config.serial}) failed"
            )

        assert programmer.start_rtt(mcu=io_config.mcu, reset=True), (
            f"RTT start failed for {io_config.mcu} (serial {io_config.serial})"
        )
        rtt = PlcRtt(programmer)

        last = ""
        for _ in range(RTT_READY_RETRIES):
            last = rtt.run("io", timeout=RTT_READY_TIMEOUT_S)
            if "Input states:" in last:
                break
            time.sleep(RTT_READY_RETRY_DELAY_S)
        else:
            pytest.fail(
                f"PLC did not respond to 'io' over RTT (serial={io_config.serial} mcu={io_config.mcu}).\n"
                f"Last output:\n{last}"
            )
    except BaseException:
        # Covers pytest.fail()'s Failed too (a BaseException, not Exception) --
        # without this, a setup failure above leaks the JLink connection, which then
        # blocks the next module/retry in the same session from connecting to it.
        programmer.stop_rtt()
        programmer.disconnect_target()
        raise

    try:
        yield rtt
    finally:
        for n in _pins_for(tb_labels, io_config.short, "OUT"):
            try:
                rtt.set_out(n, False)
            except Exception:
                pass
        for n in _pins_for(tb_labels, io_config.short, "KEY"):
            try:
                rtt.set_key(n, False)
            except Exception:
                pass
        programmer.stop_rtt()
        programmer.disconnect_target()
