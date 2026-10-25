#!/usr/bin/env python3
"""Example: toggle one output coil by its testbench.toml label name.

Reads the coil's current state, flips it via set_coils_mask(), then reads it back to
confirm -- the write call itself only ever sends a (mask, value) bit pair, resolved
locally from testbench.toml by TestbenchLabels (see testbench_client.py).

Prerequisites: same as 01_read_inputs.py.

Usage (from the repo root):
    uv run --extra ipc python testbench/examples/python/02_toggle_output.py LABEL [path/to/testbench.toml]

Example:
    uv run --extra ipc python testbench/examples/python/02_toggle_output.py USB_EMPTY
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "client" / "python"))

from testbench_client import TestbenchClient, TestbenchIpcError, TestbenchLabels  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} LABEL [path/to/testbench.toml]", file=sys.stderr)
        return 2

    label = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else str(Path(__file__).resolve().parents[2] / "testbench.toml")
    labels = TestbenchLabels.load(config_path)

    if label not in labels.output_addr:
        print(f"'{label}' is not a known output label (see testbench.toml's io.map.outputs.labels)", file=sys.stderr)
        return 2

    try:
        with TestbenchClient() as client:
            if not client.ping():
                print("testbench daemon not reachable", file=sys.stderr)
                return 1

            before = labels.decode_outputs(client.get_outputs()["bits"])[label]
            print(f"{label}: {'ON' if before else 'off'} -> {'off' if before else 'ON'}")

            mask, value = labels.build_coil_request({label: not before})
            client.set_coils_mask(mask, value)

            after = labels.decode_outputs(client.get_outputs()["bits"])[label]
            print(f"confirmed: {label} is now {'ON' if after else 'off'}")
    except TestbenchIpcError as e:
        print(f"IPC error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
