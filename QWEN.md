# BMPLC Quick Project

## Project Overview

BMPLC (Bare Metal PLC) firmware for Robotics Hardware Solutions' bare-metal PLC boards. One C11 codebase, multiple board targets selected at CMake configure time:

| Target | MCU | Core | Notes |
|---|---|---|---|
| `BMPLC_M` (default) | STM32F103RE | Cortex-M3, 72 MHz | USB (TinyUSB), CANopen, EEPROM |
| `BMPLC_L` | STM32F765ZG | Cortex-M7 | Shares F7 code with XL |
| `BMPLC_XL` | STM32F765ZG | Cortex-M7, 216 MHz (overdrive) | Ethernet, QSPI flash, RTC, speaker |
| `G0B1` (dev only) | STM32G0B1 | Cortex-M0+ | `toolchains/g0b1.cmake`, not part of CI |

Stack: FreeRTOS (statically allocated), STM32 HAL, SEGGER RTT logging/CLI, mongoose networking (+ Modbus TCP), TinyUSB (M only), co_stack CANopen (M only).

Hardware repos and user docs are linked from `README.md`.

## Building

Requirements: cmake ≥ 3.24, `arm-none-eabi-gcc`, recursive submodules (`git clone --recursive`).

```sh
mkdir build_m && cd build_m
cmake -DPLC_TYPE=BMPLC_M -DCMAKE_BUILD_TYPE=Debug ..   # PLC_TYPE: BMPLC_M | BMPLC_L | BMPLC_XL | G0B1
cmake --build .
```

- `PLC_TYPE` selects the toolchain file (`toolchains/plc_*.cmake`) and all per-target feature flags.
- Outputs in the build dir: `bmplc.elf`, `bmplc.hex`, `bmplc.bin`, `bmplc.map`; the linker prints memory usage.
- Build types: `Debug` (no optimization, **device tests compiled in**), `Release` (`-Ofast`), `RelWithDebInfo`, `MinSizeRel`, `MinOptDebInfo`.
- Device tests are only compiled in Debug or when registered with `test(fn SELFTEST)` (see `thirdparty/rhs/cmake/rhs.cmake`).
- Compiler flags/includes for analysis or IDE setup: `build/compile_commands.json` (or `cmake-build-debug/`).

## Flashing and Running Tests on Hardware

Uses `bmlab-toolkit` (`pip install bmlab-toolkit`). MCU names: `STM32F103RE` (M), `STM32F765ZG` (L/XL).

```sh
bml flash build_m/bmplc.bin --serial <JLINK_SERIAL> --mcu STM32F103RE
bml rtt   --serial <JLINK_SERIAL> --mcu STM32F103RE -t 30 --msg "?"          # list RTT CLI commands
bml rtt   --serial <JLINK_SERIAL> --mcu STM32F103RE -t 10 --no-reset --msg "memmng_test"
```

- Unit tests are RTT CLI commands on the device. List them with `?` (names end in `_test`).
- A test passes if its output contains a final `REPORT` line with `Failures: 0`.
- CI (`.github/workflows/unit_tests.yml`) does exactly this for `BMPLC_M` + `BMPLC_XL` on self-hosted runners.
- VSCode: J-Link launch/attach configs + RTT Viewer tab; `JLinkRTTClient` works standalone. Remote debugging via `JLinkRemoteServer` (see README.md).

### RTT CLI commands
`?`, `uptime`, `free`, `log`, `reset`, `uid`, `top`, `can_open` (filter/send CAN frames), `usb_bridge` (`-rs232`/`-rs485`), `mem_test`, `log_save_test`, plus all registered device tests.

## Architecture

### Startup flow (`main.c`)
`HAL_Init()` → `SystemClock_Config()` (per-target, defined in `main.c`) → `rhs_init()` → `rhs_hal_init()` → start the `init_task` thread → `vTaskStartScheduler()`.
`init_task` starts every registered service (`RHS_SERVICES[]`) and then blocks in `rhs_thread_scrub()`, which reaps terminated threads. FreeRTOS is statically allocated (idle/timer task memory provided in `main.c`).

### CMake-driven service registration
`thirdparty/rhs/cmake/rhs.cmake` defines three CMake functions that generate `${CMAKE_BINARY_DIR}/applications.c`:

- `service(handler "name" stack_bytes)` — a service is a FreeRTOS task with an infinite body `int32_t handler(void* context)`; started by `init_task`.
- `start_up(fn)` — init hook run after all services are started (apps use this to register RTT CLI commands).
- `test(fn [SELFTEST])` — registers a device test as an RTT CLI command (Debug/SELFTEST builds only).

So adding a feature = new folder with `CMakeLists.txt` (library + one of the three registration calls) under `user_apps/`, `user_tests/`, or `thirdparty/rhs/applications/services/`.

### Per-target feature gating
Toolchain files set `RHS_HAL_*` / `RHS_DRIVER_*` / `RHS_SERVICE_*` / `RHS_APPLICATION_*` / `RHS_TEST_*` flags plus `-DBMPLC_M`/`-DBMPLC_XL`. HAL modules are also pulled in **transitively** (`thirdparty/rhs/hal/CMakeLists.txt`), e.g. `RHS_SERVICE_USB_SERIAL_BRIDGE` → `rhs_hal_serial` + `rhs_hal_random`, `RHS_DRIVER_EEPROM` → `rhs_hal_i2c`. Current scope:

- **XL**: HAL flash_ex (QSPI MT25QL128ABA), io, rtc, serial, speaker, can (bxCAN), random; service `ETH_NET` (mongoose + built-in STM32F7 netif driver).
- **M**: HAL i2c + EEPROM driver, usb (TinyUSB), serial, can; services `USB_CDC_NET` (TinyUSB NCM + mongoose), `USB_SERIAL_BRIDGE`, `CAN_OPEN` (co_stack).
- The `net` service (mongoose + **modbus_tcp**, always built with net) compiles for both targets.

### Layering
- `core/` — board glue: per-family HAL conf/MSP/system files under `core/inc|src/{f1,f7,g0}`, `syscalls.c`/`sysmem.c`, `FreeRTOSConfig.h`. See `core/README.md`.
- `thirdparty/rhs/` — the RHS framework: `core/` (threads, records, queues/mutexes/semaphores/event flags — static FreeRTOS wrappers; log; memmgr), `hal/` (one module per peripheral, each with its own CMakeLists), `applications/services/` (cli, loader, net + backends, can_open, notification, usb_serial_bridge).
- `user_apps/` — application services (currently: `cdc_net_hello_rhs`, `eth_net_hello_rhs`).
- `user_tests/` — device-side tests (currently: `memmng_test`, `records_test`, `eeprom_test`, `io_test`, `flash_ex_test`).
- `thirdparty/` also holds freertos, mongoose, tinyusb, co_stack (CANopen), rcan/rserial/rtimer/runit, RTT — external libraries.
- `testbench/` — Python (uv) HIL testbench driving the board over serial/Modbus; config in `testbench/testbench.toml`.

## Creating a New Application
1. Create a new folder (e.g. `user_apps/new_app/`) with a `CMakeLists.txt`:
```cmake
cmake_minimum_required(VERSION 3.24)
project(new_app C)
set(CMAKE_C_STANDARD 11)

add_library(${PROJECT_NAME} STATIC new_app.c)
target_include_directories(${PROJECT_NAME} PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>)
target_link_libraries(${PROJECT_NAME} PRIVATE rhs rhs_hal RTT)

service(new_app "new_app" 1024)
```
2. Implement `int32_t new_app(void* context)` in `new_app.c` — an infinite loop; use `rhs_delay(ms)`, `RHS_LOG_I(TAG, ...)`, and mutexes/queues from the RHS core.
3. Build and verify with the RTT `top` command.

## Creating a Device Test
1. New folder (e.g. `user_tests/new_test/`) with a `CMakeLists.txt` ending in:
```cmake
test(new_test)                 # Debug builds only
# or: test(new_test SELFTEST)  # always included in the build
```
2. Implement `void new_test(void)` in `new_test.c`; the test framework prints a final `REPORT` line with pass/fail counts.
3. Run on hardware: `bml rtt ... --msg "new_test"` — passes when the final `REPORT` line shows `Failures: 0`.

Alternative manual pattern (README.md): register a CLI command via `cli_add_command("name", fn, NULL)` inside a `start_up(fn)` hook.

## Development Conventions
- **Fail-fast**: `rhs_assert()` / `rhs_crash(msg)` → BKPT under a debugger, else system reset. Core code has no error-recovery paths; don't add silent fallbacks.
- **Logging**: SEGGER RTT via `RHS_LOG_E/W/I/D(TAG, fmt, ...)`; each file defines its own `#define TAG`.
- **Records**: persistent named data (`rhs_record_create/open/close/destroy`). Pointers from `rhs_record_open` are only valid while the record is open.
- **rtimer**: hardware TIM1 timer, 100 µs tick; callbacks run in **ISR context** — the interval parameter is in microseconds.
- **Style**: `.clang-format` (4-space indent, 120 columns, Allman braces, left pointer alignment).
- **External libraries — do not read/search/analyze unless explicitly asked**: `thirdparty/freertos`, `mlib`, `mongoose`, `stm32f1_cmsis/hal`, `stm32f7_cmsis/hal`, `stm32g0_cmsis/hal`, `tinyusb`.
- A more detailed companion guide exists at `.claude/CLAUDE.md` (Claude Code instructions); keep the two in sync when conventions change.

## Key Files
- `CMakeLists.txt` — root build; `PLC_TYPE` → toolchain selection.
- `main.c` — startup, per-target `SystemClock_Config`, FreeRTOS static task memory hooks.
- `toolchains/plc_{m,l,xl}.cmake`, `g0b1.cmake` — per-target compiler flags, HAL sources, feature flags.
- `thirdparty/rhs/cmake/rhs.cmake` — `service()`/`start_up()`/`test()` registration; generates `applications.c`.
- `core/README.md` — board glue file map.
- `.github/workflows/unit_tests.yml` — CI: build + flash + run all `*_test` RTT commands.
- Linker scripts: `STM32F103RETX_FLASH.ld`, `STM32F765ZGTX_FLASH.ld`, `STM32G0B1KCUX_FLASH.ld`; SVD files for IDEs.
