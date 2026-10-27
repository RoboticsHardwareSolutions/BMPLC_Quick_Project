"""PlcRtt: a small command/response layer on top of bmlab_toolkit.JLinkProgrammer's
raw RTT primitives (start_rtt/rtt_write/rtt_read/stop_rtt).

bmlab-toolkit itself has no "write a line, wait for the response" helper -- its own
`bml rtt` CLI re-implements an ad hoc read loop for its own purposes (write with
retries, then poll-read-and-print until a timeout, with no response-boundary
detection at all). This module implements the equivalent for pytest fixtures/tests
that need to send one RTT command and get back the text it produced, built directly
on bmlab_toolkit's documented public methods -- not by shelling out to `bml`.

Talks to firmware registered via `user_tests/io_test/target/io_test.c`'s `io` RTT CLI
command. Note the command syntax has NO leading dash: `io key0 on`, `io out1 off`,
bare `io` to read all inputs -- despite a stale comment in io_test.c claiming
`-key0`/`-out1`.
"""

from __future__ import annotations

import re
import time

from bmlab_toolkit import JLinkProgrammer

# How long to wait, after the last non-empty rtt_read(), with nothing further arriving
# before treating a command's output as complete.
RTT_QUIET_PERIOD_S = 0.2

# Sleep between empty rtt_read() polls.
RTT_POLL_S = 0.01

_INPUT_LINE_RE = re.compile(r"IN(\d+):\s*(HIGH|LOW)")


class PlcRttError(RuntimeError):
    """Raised when the firmware's RTT response doesn't confirm a requested IO change."""


class PlcRtt:
    """Wraps one already-`start_rtt()`'d JLinkProgrammer with io_test.c's `io` command."""

    def __init__(self, programmer: JLinkProgrammer):
        self._programmer = programmer

    def run(self, msg: str, timeout: float = 5.0) -> str:
        """Write `msg` (plus a trailing newline) over RTT, then collect whatever text
        comes back until either RTT_QUIET_PERIOD_S passes with no new bytes, or
        `timeout` elapses overall -- whichever comes first.

        Always returns the accumulated text, even on a pure timeout with no quiet
        period reached -- never raises, so a caller's own assertion can report the
        partial output as context.
        """
        self._programmer.rtt_write((msg + "\n").encode("utf-8"))

        chunks: list[str] = []
        deadline = time.monotonic() + timeout
        last_data_at = time.monotonic()

        while time.monotonic() < deadline:
            data = self._programmer.rtt_read(max_bytes=4096)
            if data:
                chunks.append(data.decode("utf-8", errors="replace"))
                last_data_at = time.monotonic()
            else:
                if chunks and (time.monotonic() - last_data_at) >= RTT_QUIET_PERIOD_S:
                    break
                time.sleep(RTT_POLL_S)

        return "".join(chunks)

    def read_inputs(self, timeout: float = 5.0) -> dict:
        """Returns {0: bool, 1: bool, ...} for IN0..IN4, parsed from `io`'s output.

        Takes the LAST match per pin number, since a stale previous response can
        still be sitting in the RTT buffer ahead of the one just requested.
        """
        text = self.run("io", timeout=timeout)
        states: dict = {}
        for n, state in _INPUT_LINE_RE.findall(text):
            states[int(n)] = state == "HIGH"
        return states

    def set_out(self, n: int, on: bool, timeout: float = 5.0) -> None:
        state = "on" if on else "off"
        text = self.run(f"io out{n} {state}", timeout=timeout)
        expected = f"OUT{n} turned {'ON' if on else 'OFF'}"
        if expected not in text:
            raise PlcRttError(f"expected '{expected}' in RTT response, got:\n{text}")

    def set_key(self, n: int, on: bool, timeout: float = 5.0) -> None:
        state = "on" if on else "off"
        text = self.run(f"io key{n} {state}", timeout=timeout)
        expected = f"KEY{n} turned {'ON' if on else 'OFF'}"
        if expected not in text:
            raise PlcRttError(f"expected '{expected}' in RTT response, got:\n{text}")
