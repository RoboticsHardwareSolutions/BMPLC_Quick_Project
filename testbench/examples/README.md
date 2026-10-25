# testbench API examples

Minimal, runnable examples of the two ways to talk to a running `testbench` daemon
from outside it: the low-latency NNG IPC API, in C and in Python. Both languages use
the same wire protocol (`testbench/include/testbench_proto.h`) and the same design:

- **The wire protocol is label-free.** A client only ever sends/receives bit positions
  and 32-bit coil masks -- never label strings. Label names are resolved *locally*,
  by parsing `testbench.toml` yourself (the same file the daemon reads).
- **Input bits** are absolute bit indices (bit *i* of the 32-bit mask = the bit at
  index *i* in `io.map.inputs.labels`).
- **Output coils** are addressed relative to `output_min_addr` (the lowest coil
  address used by any label in `io.map.outputs.labels` -- see
  `testbench/src/config.c`'s comments for why this isn't simply
  `io.map.outputs.start_address`). Bit *i* of a mask/value pair = coil
  `output_min_addr + i`. The mask is a `uint32_t`, so only a 32-coil span can be
  addressed this way -- both examples below check for this and fail clearly if a
  label falls outside it.

Each example comes in two flavors:

| | bare wire API (no label resolution) | realistic usage (labels from `testbench.toml`) |
|---|---|---|
| C | [`c/01_read_inputs.c`](c/01_read_inputs.c) | [`c/02_toggle_output.c`](c/02_toggle_output.c) |
| Python | -- | [`python/01_read_inputs.py`](python/01_read_inputs.py), [`python/02_toggle_output.py`](python/02_toggle_output.py) |

(Python's `TestbenchClient`/`TestbenchLabels` split already makes label resolution
trivial, so there's no separate "bare" Python example -- see
`testbench/client/python/testbench_client.py` if you want to skip `TestbenchLabels`
and send raw bit positions yourself, exactly like the C example does.)

## Prerequisite: a running daemon

All examples talk to an **already-running** `testbench` daemon over its IPC socket
(default `ipc:///tmp/testbench.ipc`) -- they never touch the serial port themselves.
Start one first, from `testbench/`:

```sh
cd testbench/build   # after the normal `cmake .. && cmake --build .` (see testbench/CMakeLists.txt)
./testbench --config ../testbench.toml
```

## C examples

Built as extra targets in the daemon's own `testbench/CMakeLists.txt` -- no separate
build setup needed:

```sh
cd testbench/build
cmake --build . --target example_read_inputs example_toggle_output

./example_read_inputs
./example_toggle_output USB_EMPTY ../testbench.toml
```

- **`01_read_inputs.c`** -- the minimal form of the API: connect, ping, read the raw
  32-bit input mask with `tb_client_get_inputs()`, print which bits are set. No TOML
  parsing, no extra dependencies beyond `testbench_client.h` itself.
- **`02_toggle_output.c`** -- links against the daemon's own `config.c` (+ `tomlc17`)
  to parse `testbench.toml` and resolve a label name to a bit position with
  `tb_config_find_output_addr()`, then flips it with `tb_client_set_coils_mask()` and
  reads it back to confirm. This is the pattern a real application should follow.

Full C API reference: `testbench/client/c/testbench_client.h` (doc comments on every
function) and `testbench/include/testbench_proto.h` (wire format, if you want to
reimplement the client in another language).

## Python examples

Require the optional `pynng` dependency (not part of the core HIL test deps). From
the **repo root**:

```sh
uv sync --extra ipc

uv run --extra ipc python testbench/examples/python/01_read_inputs.py
uv run --extra ipc python testbench/examples/python/02_toggle_output.py USB_EMPTY
```

Both scripts accept an optional config path as their last argument (default:
`testbench/testbench.toml`).

- **`01_read_inputs.py`** -- `TestbenchLabels.load()` parses `testbench.toml` once,
  `TestbenchClient.get_inputs()` fetches the raw bitmask, `decode_inputs()` turns it
  into a `{label: bool}` dict.
- **`02_toggle_output.py`** -- reads the current state of one output label, builds a
  `(mask, value)` pair with `TestbenchLabels.build_coil_request()`, writes it with
  `set_coils_mask()`, reads back to confirm.

Full Python API reference: `testbench/client/python/testbench_client.py` (doc
comments on `TestbenchClient` and `TestbenchLabels`).

## Picking a label to experiment with

`USB_EMPTY` (used by both `02_*` examples above) is the one output coil in the
stand's default `testbench.toml` that isn't wired to anything -- safe to toggle
without affecting a connected PLC board. Run `./testbench --list` (or inspect
`testbench.toml`'s `[io.map.outputs.labels]`) for the full set of labels on your
stand before experimenting with any other one.
