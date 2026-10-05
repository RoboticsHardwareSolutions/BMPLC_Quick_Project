"""RTT CLI wrapper around bmlab-toolkit (`bml rtt` / `bml flash`).

Shared HIL infrastructure: used by the root conftest.py fixtures and by
device-side testbench scripts. Follows the invocation pattern from
.github/workflows/unit_tests.yml:

- first call after power-on/flash is made WITHOUT --no-reset (resets the
  board and gives it time to boot), subsequent calls use --no-reset;
- RTT text is captured from stdout+stderr and parsed with regexes.
"""

import logging
import re
import shutil
import subprocess

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Extra seconds on top of the RTT wait (-t) for the subprocess timeout.
_SUBPROCESS_TIMEOUT_MARGIN = 30


class BmlError(RuntimeError):
    """Raised when the bml CLI is missing or a command fails."""


def _require_bml() -> None:
    if shutil.which("bml") is None:
        raise BmlError(
            "bml CLI not found in PATH. Install bmlab-toolkit (pip install bmlab-toolkit) "
            "or activate the environment that provides it."
        )


def flash(bin_path: str, serial: str, mcu: str) -> None:
    """Flash firmware with `bml flash`. Raises BmlError on failure."""
    _require_bml()
    cmd = ["bml", "flash", str(bin_path), "--serial", serial, "--mcu", mcu]
    logger.info(f"Flashing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        raise BmlError(f"bml flash failed (exit {result.returncode}):\n{output}")
    logger.info("Flash completed.")


class PlcRtt:
    """Runs RTT CLI commands on a PLC via `bml rtt` and parses their output."""

    def __init__(self, serial: str, mcu: str, timeout: int = 10):
        self.serial = serial
        self.mcu = mcu
        self.timeout = timeout

    def run(self, msg: str, reset_board: bool = False, timeout: int | None = None) -> str:
        """Send an RTT CLI command and return the captured output.

        reset_board=True omits --no-reset: the board is reset first (use for
        the very first call after power-on/flash). timeout overrides the RTT
        wait (-t) for this call.
        """
        _require_bml()
        rtt_timeout = self.timeout if timeout is None else timeout
        cmd = ["bml", "rtt", "--serial", self.serial, "--mcu", self.mcu, "-t", str(rtt_timeout)]
        if not reset_board:
            cmd.append("--no-reset")
        cmd += ["--msg", msg]

        logger.info(f"RTT: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=rtt_timeout + _SUBPROCESS_TIMEOUT_MARGIN
            )
        except subprocess.TimeoutExpired as e:
            raise BmlError(f"bml rtt timed out after {rtt_timeout + _SUBPROCESS_TIMEOUT_MARGIN}s: {e}") from e

        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            raise BmlError(f"bml rtt failed (exit {result.returncode}):\n{output}")
        return output

    def read_inputs(self) -> dict[int, bool]:
        """Run `io` and parse input states. Returns {pin: is_high}.

        The RTT buffer may contain stale lines from previous commands, so the
        last occurrence of each pin wins.
        """
        output = self.run("io")
        states: dict[int, bool] = {}
        for match in re.finditer(r"IN(\d):\s*(HIGH|LOW)", output):
            states[int(match.group(1))] = match.group(2) == "HIGH"
        return states

    def set_out(self, n: int, on: bool) -> None:
        """Run `io out<n> on|off` and verify the firmware acknowledged it."""
        state = "on" if on else "off"
        output = self.run(f"io out{n} {state}")
        expected = f"OUT{n} turned {'ON' if on else 'OFF'}"
        if expected not in output:
            raise BmlError(f"PLC did not confirm '{expected}'. Output:\n{output}")

    def set_key(self, n: int, on: bool) -> None:
        """Run `io key<n> on|off` and verify the firmware acknowledged it."""
        state = "on" if on else "off"
        output = self.run(f"io key{n} {state}")
        expected = f"KEY{n} turned {'ON' if on else 'OFF'}"
        if expected not in output:
            raise BmlError(f"PLC did not confirm '{expected}'. Output:\n{output}")
