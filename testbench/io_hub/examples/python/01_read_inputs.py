#!/usr/bin/env python3
"""Example: read and decode all input bits from a running testbench daemon.

This is the "realistic usage" style: TestbenchLabels parses testbench.toml once to
build label <-> bit maps, and TestbenchClient only ever exchanges raw bit positions
over IPC -- the same split testbench_client.h's C API uses (see
examples/c/02_toggle_output.c for the C equivalent).

Prerequisites:
    - a testbench daemon must already be running, e.g. from testbench/io_hub/:
          ./build/testbench --config ../testbench.toml
    - `pynng`, a core dependency of the repo-root pyproject.toml:
          uv sync

Usage (from the repo root):
    uv run python testbench/io_hub/examples/python/01_read_inputs.py [path/to/testbench.toml]

    If no config path is given, defaults to testbench/testbench.toml.
"""

import sys
from pathlib import Path

# testbench_client.py lives in testbench/client/python/, not on sys.path by default.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "client" / "python"))

from testbench_client import TestbenchClient, TestbenchIpcError, TestbenchLabels  # noqa: E402


def main() -> int:
    config_path = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[3] / "testbench.toml")
    labels = TestbenchLabels.load(config_path)

    try:
        with TestbenchClient() as client:
            if not client.ping():
                print("testbench daemon not reachable", file=sys.stderr)
                return 1

            inputs = client.get_inputs()
            print(f"snapshot: valid={inputs['valid']} ts_ms={inputs['ts_ms']}")
            for name, on in sorted(labels.decode_inputs(inputs["bits"]).items()):
                print(f"  {name:<20} {'ON' if on else 'off'}")
    except TestbenchIpcError as e:
        print(f"IPC error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
