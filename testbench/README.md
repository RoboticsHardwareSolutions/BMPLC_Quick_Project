# testbench

A C daemon for the HIL test stand's Modbus RTU hub: continuously polls/holds the
stand's I/O over RS485, and exposes that state to the outside world three ways — a
one-shot CLI, a web control panel, and a low-latency IPC API (C and Python).

## Why a daemon

The stand's two Modbus RTU I/O modules (inputs exposed as Holding Registers, outputs
as Coils) have a **bus-error watchdog**: if no master talks to them for longer than a
threshold (device default ~2s), they reset/hold their output state until
communication resumes. A tool that only opens the serial port for the duration of a
single call has nothing keeping the bus alive in between calls, and nothing letting an
external process both read live input state and hold a desired output state at low
latency.

`testbench`'s poll thread owns the serial port exclusively and, every cycle (default
200 ms, `io.connection.poll_interval_ms`):

1. reads the input holding registers (`inputs_id`) into an in-memory 32-bit mask;
2. **unconditionally rewrites the full output coil span** (`outputs_id`) from an
   in-memory "desired state" cache — even when nothing changed. This is what defeats
   the watchdog; everything else (CLI, HTTP, IPC) only ever mutates that cache, never
   talks to the serial port directly while a daemon is running.

## Build

Requirements: `cmake` ≥ 3.24, a C11 host compiler, and `autoconf`/`automake`/`libtool`
(used once, to generate `libmodbus`'s `config.h` — see below).

```sh
cd testbench
mkdir -p build && cd build
cmake ..
cmake --build . --target testbench
```

This is a **standalone, host-native** build — `testbench/CMakeLists.txt` is never
`add_subdirectory()`'d from the repo-root build (which forces an ARM cross-toolchain
before `project()`). It pulls in three git submodules under `../thirdparty/` that
belong to this tool specifically:

| Submodule | Used for |
|---|---|
| `thirdparty/tomlc17` | parsing `testbench.toml` (compiled directly, single `.c`/`.h` pair, no build system of its own) |
| `thirdparty/libmodbus` | Modbus RTU master — only `modbus.c`/`modbus-data.c`/`modbus-rtu.c` are built (the TCP backend is skipped: unused, and doesn't compile on macOS) |
| `thirdparty/nng` | the IPC transport (see below) — **must stay pinned to a stable `v1.x` tag** (currently `v1.12.5`); the `nng` default branch panics on `nng_req0_open`/`nng_rep0_open` |

`thirdparty/mongoose` (already vendored for the firmware) is reused for the HTTP
server, rebuilt here a second time as a host-native static library — the firmware's
own `mongoose` CMake target is cross-compiled for ARM and can't be linked into a host
binary.

`libmodbus`'s `config.h` is generated once via `autogen.sh` + `configure` on first
configure (skipped on subsequent `cmake` runs once `config.h` exists).

### Extra build targets

```sh
cmake --build . --target testbench_client        # the C IPC client library, standalone
cmake --build . --target example_read_inputs      # examples/, see examples/README.md
cmake --build . --target example_toggle_output
```

## Configuration — `testbench.toml`

```toml
[io.connection]
    port = "/dev/cu.usbserial-XXXX"   # macOS: use /dev/cu.*, not /dev/tty.* -- see Troubleshooting
    inputs_id = 1                     # Modbus slave ID exposing inputs as Holding Registers
    ouputs_id = 2                     # (sic -- matches the existing typo'd key) outputs as Coils
    baudrate = 115200
    timeout = 1.5                     # per-transaction response timeout, seconds
    retries = 3                       # one-shot CLI/seed transactions only; see below
    # poll_interval_ms = 200          # optional, daemon poll cycle period; defaults to 200

[io.map.inputs]
    start_address = 0
    count = 2                         # 16-bit holding registers -> 32 input bits
    [io.map.inputs.labels]            # "bit index" = "label name"
        "6" = "PLC_M_OUT0"
        ...

[io.map.outputs]
    [io.map.outputs.labels]           # "coil address" = "label name"
        "5" = "PWR_PLC_M"
        ...

[iface.canbus]
    port = "/dev/tty.usbserial-XXXX"  # presence-only check (stat(), never opened)
[iface.rs422]
    ...
```

Every label shown anywhere by this tool — CLI output, the web UI, the HTTP JSON API —
comes directly from `[io.map.inputs.labels]`/`[io.map.outputs.labels]`; nothing is
hardcoded.

**Output coil addressing note:** the active coil range is derived from the *label
table itself* (min..max address actually used by a label), not from
`io.map.outputs.start_address`/`count` — those two keys are parsed but intentionally
unused for addressing, since the label table is the only part of this config
guaranteed to reflect the actual wiring. `src/config.c` computes this once at
startup; see its comments for the full rationale.

**`retries`:** honored by one-shot CLI transactions and the daemon's startup output
seed (real RS485 lines occasionally glitch a single frame) — *not* by the daemon's
main poll cycle, which already gets an implicit retry from its next cycle 200ms later.

## Running as a daemon

```sh
./testbench --config ../testbench.toml                 # foreground (default)
./testbench --config ../testbench.toml -d               # detached, background
```

| Flag | Default | Meaning |
|---|---|---|
| `--config PATH` | `testbench.toml` | path to the TOML config |
| `-d`, `--daemonize` | off | classic double-fork: detach from the terminal, run in the background |
| `--pidfile PATH` | `/tmp/testbench.pid` | written after daemonizing, removed on clean shutdown |
| `--log-file PATH` | `/tmp/testbench.log` (daemonized only) | stdout/stderr target once daemonized; foreground mode always logs to the terminal |
| `--http-addr URL` | `http://0.0.0.0:8080` | Mongoose listen address |
| `--web-root DIR` | `web` (relative to CWD) | static files for the control panel |
| `--no-http` | off | skip starting the HTTP server entirely |

Foreground mode prints a live one-line status (`inputs=0x... outputs=0..15 polls=N
errors=N ok`) updated every poll cycle; daemonized mode logs only state-change events
(startup, shutdown) to `--log-file`, since a daemon's log isn't a terminal. Either
way, `Ctrl+C` / `SIGTERM` triggers a clean shutdown: the HTTP and IPC listeners stop,
the serial port closes, and (if daemonized) the pidfile is removed.

**Relative `--web-root`/`--pidfile`/`--log-file` are resolved to absolute paths
*before* daemonizing** (`tb_daemonize()`'s `chdir("/")` would otherwise break a
relative path appended afterwards) — safe to pass as given from any working
directory.

## One-shot CLI

```sh
./testbench --config ../testbench.toml --list                        # dump all labels (no I/O)
./testbench --config ../testbench.toml --read                        # read & decode all inputs
./testbench --config ../testbench.toml --write USB_EMPTY=1            # set one or more output coils
./testbench --config ../testbench.toml --write USB_EMPTY=1,PWR_PLC_M=0
./testbench --config ../testbench.toml --iface                       # presence-check [iface.*] ports
./testbench --config ../testbench.toml --status                      # requires a running daemon
```

`--read`/`--write`/`--status` are **daemon-aware**: if a `testbench` daemon is already
listening on the IPC socket, the command routes through it (safe — doesn't contend
for the serial port with the daemon's poll thread). If no daemon is running,
`--read`/`--write` fall back to a direct, short-lived Modbus session (open, transact,
close); `--status` has nothing to report without a daemon and fails with a clear
error instead.

`--write`'s read-modify-write (direct-session fallback) only touches the coils it was
asked to change — the surrounding span is read first and patched, never blindly
zeroed. The daemon-routed path instead mutates the daemon's persistent desired-state
cache directly (no read-before-write needed — the cache is always authoritative).

`--list` and `--iface` never touch the serial port or the daemon (`--list` only reads
the config; `--iface` is a `stat()` against each `[iface.*]` path — presence-only,
never captures the port).

## Web control panel

```sh
./testbench --config ../testbench.toml   # then open http://localhost:8080/
```

Static files in `web/` (`index.html`/`style.css`/`app.js`, plain files on disk —
served with `mg_http_serve_dir()`, no build/packing step). Shows live input/output
state (labels from `testbench.toml`), toggle switches for outputs, and presence
badges for the four `[iface.*]` adapters, polling `GET /api/state` every 300ms.

REST API (JSON):

| Endpoint | Method | Description |
|---|---|---|
| `/api/state` | GET | `{inputs, outputs, iface, status}` — full snapshot, same label names as `testbench.toml` |
| `/api/outputs` | POST | body `{"LABEL": true\|false, ...}` — merges into the desired-state cache |

## Low-latency IPC API (C & Python)

For external processes that need lower latency / don't want to shell out to the CLI
or poll HTTP: a compact binary protocol over NNG `REQ`/`REP`
(`ipc:///tmp/testbench.ipc` by default), defined in
[`include/testbench_proto.h`](include/testbench_proto.h). Deliberately **label-free**
on the wire — clients resolve label names locally from `testbench.toml` (same file,
same semantics as `src/config.c`) and only ever exchange bit positions / 32-bit coil
masks.

- **C client:** [`client/c/testbench_client.h`](client/c/testbench_client.h) /
  `.c` — `tb_client_connect()`, `tb_client_get_inputs()`,
  `tb_client_get_outputs()`, `tb_client_set_coils_mask()`, `tb_client_get_status()`,
  `tb_client_ping()`.
- **Python client:** [`client/python/testbench_client.py`](client/python/testbench_client.py)
  — `TestbenchClient` (the same calls) + `TestbenchLabels` (parses `testbench.toml`,
  does label <-> bit translation, builds `set_coils_mask()` requests from a
  `{label: bool}` dict). Needs the optional `pynng` dependency:
  `uv sync --extra ipc` from the repo root.

**Full worked examples with their own documentation:** [`examples/README.md`](examples/README.md)
(`examples/c/`, `examples/python/`) — one minimal/bare example and one realistic
label-resolving example per language, all verified against real hardware.

## Troubleshooting

- **Two processes can't share the port:** only one process may hold the serial port
  at a time — if anything else (another `testbench` instance, a one-off script, a
  debugging session) has it open, every transaction here will fail or contend for the
  bus. Make sure nothing else is pointed at the same `[io.connection].port` before
  starting a daemon.
- **Every Modbus transaction times out, but the port opens fine:** on macOS, use
  `/dev/cu.usbserial-*`, not `/dev/tty.usbserial-*` — the `tty.*` node blocks on
  carrier-detect semantics this kind of USB-serial adapter never satisfies.
- **The configured port doesn't exist:** this adapter's device-node ID can drift
  across reconnects/different USB ports (it isn't a fixed-serial FTDI device like the
  `[iface.*]` adapters are). Compare `ls /dev/tty.usbserial-* /dev/cu.usbserial-*`
  against `[io.connection].port` and update it if needed.
- **`nng_req0_open`/`nng_rep0_open` aborts with an `assert` panic:** the `nng`
  submodule drifted off the pinned `v1.x` tag onto an unstable pre-release commit —
  `cd ../thirdparty/nng && git checkout v1.12.5` (or whatever the current pin is).
- **Occasional single "Invalid CRC" / transient read-write failure from the CLI:**
  normal RS485 bus noise, especially right after (re)connecting cables — covered by
  `retries` (see Configuration above); the daemon's own poll loop self-heals within
  one cycle regardless.
