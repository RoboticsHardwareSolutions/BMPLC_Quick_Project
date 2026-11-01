"""Runs every on-target "unit test" (runit-based CLI command whose name
contains "_test") currently exposed over RTT by whatever firmware is
flashed/running -- the local-pytest equivalent of
.github/workflows/unit_tests.yml's "Run unit tests" step.

Unlike every other user_tests/<name>/testbench/<name>.py module, this one has
no user_tests/unit_test/target/unit_test.c counterpart: the on-target test
bodies already live, registered via cli_add_command()+test() in
thirdparty/rhs/cmake/rhs.cmake, inside
user_tests/{eeprom_test,memmng_test,records_test,flash_ex_test}/ -- this file
only adds a host-side way to discover+run+assert on all of them at once (CLI
command names don't always match folder names, e.g. memmng_test's folder
registers the command "mem_test", so there's no static 1:1 mapping to drive
per-command pytest.mark.parametrize from).

Requires a Debug (or SELFTEST-registered) build: `test()`'s CMake gate
(thirdparty/rhs/cmake/rhs.cmake) only compiles *_test CLI commands in when
CMAKE_BUILD_TYPE is exactly "Debug" (or SELFTEST is passed) -- any other
build type (Release, RelWithDebInfo, ...) will show zero _test commands
over '?' -- this module fails loudly in that case rather than reporting a
silent, meaningless "0 ran, 0 failed" pass.

Run against hardware with, e.g.:
    PLC_TYPE=BMPLC_M PLC_BIN=cmake-build-debug/bmplc.bin \
      uv run pytest user_tests/unit_test/testbench/ -v
"""

from __future__ import annotations

import os

import pytest

from testbench.pyhil.unit_tests import list_unit_test_commands, run_unit_test

pytestmark = pytest.mark.skipif(
    not os.environ.get("PLC_TYPE"),
    reason="on-target unit tests require hardware: set PLC_TYPE=BMPLC_M|BMPLC_XL (see conftest.py)",
)


def test_on_target_unit_tests(plc):
    names = list_unit_test_commands(plc)
    if not names:
        pytest.fail(
            "No *_test CLI commands found over RTT -- is the flashed firmware "
            "built with -DCMAKE_BUILD_TYPE=Debug? (RHS_TEST_* flags only compile "
            "in for Debug/SELFTEST builds, see thirdparty/rhs/cmake/rhs.cmake)"
        )

    reports = [run_unit_test(plc, name) for name in names]
    failed = [r for r in reports if not r.ok]
    if failed:
        details = "\n\n".join(
            f"{r.name}: "
            + (
                f"{r.failures} failure(s) (passes={r.passes})\n{r.raw}"
                if r.failures is not None
                else f"no REPORT line found\n{r.raw}"
            )
            for r in failed
        )
        pytest.fail(f"{len(failed)}/{len(reports)} on-target unit test(s) failed:\n\n{details}")
