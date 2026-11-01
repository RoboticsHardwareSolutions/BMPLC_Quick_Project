"""On-target runit-based "unit test" discovery/execution over RTT.

Talks to whatever `cli_add_command()`-registered CLI commands a Debug (or
SELFTEST-built) firmware exposes whose name contains "_test" (see
user_tests/{eeprom_test,memmng_test,records_test,flash_ex_test}/), and parses
each one's `runit_report()` output line. Built on PlcRtt.run() -- the same
generic "send a line, get back text" primitive io_test.c's `io` command uses;
this is simply a different on-target protocol layered on top of it. No
subprocess/CLI shelling out anywhere here -- PlcRtt.run() goes straight
through bmlab_toolkit.JLinkProgrammer's rtt_write()/rtt_read() methods.

Mirrors .github/workflows/unit_tests.yml's bash logic (send "?", filter
tokens containing "_test", run each, parse the REPORT line, tail -1) but
deliberately does NOT mirror its fail-open fallback: the bash script
extracts only the trailing failure count from the matched REPORT line and defaults
to "0" (pass) if even that narrow regex fails to match, which would mask a
real failure behind a reporting-format change. Here, failing to find a
`Failures:` count on a REPORT line is treated as a failure, not a pass (see
UnitTestReport.ok) -- fail-closed, not fail-open. `File:`/`Test case:` are
parsed on a best-effort basis (optional) since they're diagnostic-only; only
`Passes:`/`Failures:` are required for a line to count as a report.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from testbench.pyhil.rtt import PlcRtt, PlcRttError

_REPORT_LINE_RE = re.compile(r"^.*REPORT.*$", re.MULTILINE)
_FILE_RE = re.compile(r"File:\s*(\S+)")
_CASE_RE = re.compile(r"Test case:\s*(\S+)")
_PASSES_RE = re.compile(r"Passes:\s*(\d+)")
_FAILURES_RE = re.compile(r"Failures:\s*(\d+)")


def list_unit_test_commands(rtt: PlcRtt, timeout: float = 5.0) -> list[str]:
    """Send `?` and return sorted, de-duplicated CLI command names containing
    "_test" -- same substring filter as CI's `grep "_test"`, applied to the
    whitespace-split (`%-30s`-padded, 3-column) `cli_commands()` output.

    `cli_commands()` (thirdparty/rhs/applications/services/cli/cli_app.c)
    always ends its output with a trailing "\\r\\n" (after the last full row
    of 3, or after the remainder) and prints nothing afterwards (no prompt
    echo) -- so a response that doesn't end in "\\r\\n" is distinguishable
    from a genuinely-empty-but-complete command list, and means PlcRtt.run()
    hit its overall `timeout` mid-dump rather than a true quiet-period end.
    Silently returning a truncated subset here would under-report what's
    actually registered, so raise instead of guessing.
    """
    text = rtt.run("?", timeout=timeout)
    if not text.endswith("\r\n"):
        raise PlcRttError(
            f"'?' response looks truncated (no trailing CRLF after the last "
            f"command -- RTT link may be slow, or {timeout}s wasn't enough "
            f"time for the full listing):\n{text}"
        )
    return sorted({tok for tok in text.split() if "_test" in tok})


@dataclass(frozen=True)
class UnitTestReport:
    name: str  # the CLI command name sent, e.g. "mem_test"
    passes: int | None
    failures: int | None
    file: str | None
    test_case: str | None
    raw: str  # full RTT response text, for failure messages

    @property
    def ok(self) -> bool:
        # failures is None (no REPORT line, or no Failures: count on it) counts
        # as not-ok -- fail-closed, see module docstring.
        return self.failures == 0


def run_unit_test(rtt: PlcRtt, name: str, timeout: float = 10.0) -> UnitTestReport:
    """Send `name` over RTT and parse the LAST REPORT line in the response
    (tail -1, same as CI -- a stale REPORT from a previous run sitting ahead
    of this one in the buffer must not be mistaken for this run's result).

    File:/Test case:/Passes:/Failures: are each matched independently (not as
    one atomic sequence) so a field reorder or an added field in
    `runit_report()`'s format doesn't break extraction -- only a missing
    `Failures:` count turns into a `None` (treated as a failure, see
    UnitTestReport.ok)."""
    text = rtt.run(name, timeout=timeout)
    lines = _REPORT_LINE_RE.findall(text)
    if not lines:
        return UnitTestReport(name, None, None, None, None, raw=text)
    line = lines[-1]

    failures_match = _FAILURES_RE.search(line)
    if failures_match is None:
        return UnitTestReport(name, None, None, None, None, raw=text)

    passes_match = _PASSES_RE.search(line)
    file_match = _FILE_RE.search(line)
    case_match = _CASE_RE.search(line)
    return UnitTestReport(
        name,
        int(passes_match[1]) if passes_match else None,
        int(failures_match[1]),
        file_match[1] if file_match else None,
        case_match[1] if case_match else None,
        raw=text,
    )
