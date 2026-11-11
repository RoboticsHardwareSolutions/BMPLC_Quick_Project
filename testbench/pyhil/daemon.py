"""Subprocess lifecycle wrapper for the io_hub `testbench` daemon.

The daemon owns the stand's RS485/Modbus link exclusively; only one instance may run
at a time (see testbench/io_hub/README.md "Two processes can't share the port"). This
module starts it in foreground mode (never `-d`/`--daemonize`) so a Python test
session can supervise it directly with a plain PID and SIGTERM, rather than racing a
double-fork or polling a pidfile that foreground mode never writes.
"""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Checked in order; the first existing, executable file wins. The first entry is the
# documented, canonical out-of-source build location (see testbench/io_hub/README.md);
# the second is an IDE-generated build dir (CLion's default), kept as a fallback since
# it's what's actually present in a fresh checkout that was built via an IDE rather
# than the documented CLI steps.
_CANDIDATE_BINARIES = (
    REPO_ROOT / "testbench" / "io_hub" / "build" / "testbench",
    REPO_ROOT / "testbench" / "io_hub" / "cmake-build-debug" / "testbench",
)

_POLL_INTERVAL_S = 0.1


class IoHubDaemonError(RuntimeError):
    """Raised when the daemon binary can't be found, or fails to come up."""


def resolve_daemon_binary() -> Path:
    """Locate the `testbench` daemon binary.

    `TESTBENCH_BIN` env var, if set, is an absolute override -- fails loudly if it
    doesn't point at an existing file rather than silently falling back. Otherwise
    tries `_CANDIDATE_BINARIES` in order.
    """
    override = os.environ.get("TESTBENCH_BIN")
    if override:
        path = Path(override)
        if not path.is_file():
            raise IoHubDaemonError(f"TESTBENCH_BIN={override} does not point at an existing file")
        return path

    for candidate in _CANDIDATE_BINARIES:
        if candidate.is_file():
            return candidate

    tried = "\n".join(f"  - {c}" for c in _CANDIDATE_BINARIES)
    raise IoHubDaemonError(
        "could not find the io_hub 'testbench' daemon binary. Tried:\n"
        f"{tried}\n"
        "Build it (see testbench/io_hub/README.md) or set TESTBENCH_BIN to an explicit path."
    )


class IoHubDaemon:
    """Starts/stops one `testbench --config ... --no-http` subprocess."""

    def __init__(self, binary: Path, config_path: Path):
        self._binary = binary
        self._config_path = config_path
        self._proc: subprocess.Popen | None = None
        self._log_file = None

    def start(self, ping, startup_timeout: float = 5.0) -> None:
        """Launch the daemon in foreground mode and wait until `ping()` succeeds.

        `ping` is a zero-arg callable returning bool (typically a fresh
        TestbenchClient's `.ping`) -- passed in rather than imported here so this
        module has no hard dependency on `pynng` being importable just to manage the
        subprocess.

        stdout/stderr go to a real temp file, not subprocess.PIPE: the daemon logs one
        line per poll cycle (default every 200ms) for its entire foreground lifetime,
        which fills a pipe's fixed OS buffer within minutes if nothing drains it --
        and nothing here does, since the only read of self._proc.stdout was in the
        early-exit branch below. A plain file has no such limit.
        """
        self._log_file = tempfile.NamedTemporaryFile(mode="w+", prefix="testbench-daemon-", suffix=".log")
        self._proc = subprocess.Popen(
            [str(self._binary), "--config", str(self._config_path), "--no-http"],
            stdout=self._log_file,
            stderr=subprocess.STDOUT,
        )

        deadline = time.monotonic() + startup_timeout
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                raise IoHubDaemonError(
                    f"testbench daemon exited early (code {self._proc.returncode}):\n{self._read_log()}"
                )
            if ping():
                return
            time.sleep(_POLL_INTERVAL_S)

        self.stop()
        raise IoHubDaemonError(f"testbench daemon did not respond to ping() within {startup_timeout}s")

    def _read_log(self) -> str:
        if self._log_file is None:
            return ""
        self._log_file.seek(0)
        return self._log_file.read()

    def stop(self, term_timeout: float = 5.0) -> None:
        """SIGTERM the daemon and wait for clean shutdown; SIGKILL as a last resort.

        No-op if `start()` was never called or the process already exited.
        """
        if self._proc is None:
            return
        if self._proc.poll() is not None:
            self._proc = None
            return

        self._proc.send_signal(signal.SIGTERM)
        try:
            self._proc.wait(timeout=term_timeout)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait(timeout=term_timeout)
        finally:
            self._proc = None
            if self._log_file is not None:
                self._log_file.close()
                self._log_file = None
