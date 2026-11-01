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
tokens containing "_test", run each, parse the REPORT line, tail -1, nonzero
or missing Failures = failure) so results obtained here and in CI agree.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from testbench.pyhil.rtt import PlcRtt

_REPORT_RE = re.compile(
    r"REPORT\s*\|\s*File:\s*(?P<file>\S+)\s*\|\s*Test case:\s*(?P<case>\S+)"
    r"\s*\|\s*Passes:\s*(?P<passes>\d+)\s*\|\s*Failures:\s*(?P<failures>\d+)"
)


def list_unit_test_commands(rtt: PlcRtt, timeout: float = 5.0) -> list[str]:
    """Send `?` and return sorted, de-duplicated CLI command names containing
    "_test" -- same substring filter as CI's `grep "_test"`, applied to the
    whitespace-split (`%-30s`-padded, 3-column) `cli_commands()` output."""
    text = rtt.run("?", timeout=timeout)
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
        # failures is None (no REPORT line found at all) counts as not-ok,
        # mirroring the bash script's "No REPORT found" -> HAS_FAILURES=1 branch.
        return self.failures == 0


def run_unit_test(rtt: PlcRtt, name: str, timeout: float = 10.0) -> UnitTestReport:
    """Send `name` over RTT and parse the LAST REPORT line in the response
    (tail -1, same as CI -- a stale REPORT from a previous run sitting ahead
    of this one in the buffer must not be mistaken for this run's result)."""
    text = rtt.run(name, timeout=timeout)
    matches = list(_REPORT_RE.finditer(text))
    if not matches:
        return UnitTestReport(name, None, None, None, None, raw=text)
    m = matches[-1]
    return UnitTestReport(
        name, int(m["passes"]), int(m["failures"]), m["file"], m["case"], raw=text
    )
