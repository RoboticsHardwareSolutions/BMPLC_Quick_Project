#!/usr/bin/env python3
"""Example: ask a running testbench daemon whether one [iface.*] interface
(canbus/rs422/rs485/rs232) is available right now.

TestbenchClient.iface_available() returns False uniformly whether the daemon didn't
respond, the interface isn't configured in this stand's testbench.toml, or it's
configured but not currently detected -- other test utilities are expected to treat
all three the same way: this interface isn't usable right now.

Prerequisites:
    - a testbench daemon must already be running, e.g. from testbench/io_hub/:
          ./build/testbench --config ../testbench.toml
    - `pynng`, a core dependency of the repo-root pyproject.toml:
          uv sync

Usage (from the repo root):
    uv run python testbench/io_hub/examples/python/03_check_iface.py <canbus|rs422|rs485|rs232>
"""

import sys
from pathlib import Path

# testbench_client.py lives in testbench/client/python/, not on sys.path by default.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "client" / "python"))

from testbench_client import (  # noqa: E402
    TB_IFACE_CANBUS,
    TB_IFACE_RS232,
    TB_IFACE_RS422,
    TB_IFACE_RS485,
    TestbenchClient,
)

_IFACE_BY_NAME = {
    "canbus": TB_IFACE_CANBUS,
    "rs422": TB_IFACE_RS422,
    "rs485": TB_IFACE_RS485,
    "rs232": TB_IFACE_RS232,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in _IFACE_BY_NAME:
        print(f"usage: {sys.argv[0]} <{'|'.join(_IFACE_BY_NAME)}>", file=sys.stderr)
        return 1
    name = sys.argv[1]

    with TestbenchClient() as client:
        if not client.ping():
            print("testbench daemon not reachable", file=sys.stderr)
            return 1

        available, path = client.iface_available(_IFACE_BY_NAME[name])
        print(f"{name}: available ({path})" if available else f"{name}: not available")
        return 0 if available else 1


if __name__ == "__main__":
    raise SystemExit(main())
