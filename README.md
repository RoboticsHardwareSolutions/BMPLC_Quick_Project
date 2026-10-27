# BMPLC Quick Project

## Hardware
- [BMPLC_M](https://github.com/RoboticsHardwareSolutions/BareMetal-PLC-M)
- [BMPLC_L](https://github.com/RoboticsHardwareSolutions/BareMetal-PLC-L)
- [BMPLC_XL](https://github.com/RoboticsHardwareSolutions/BareMetal-PLC-XL)
- [User Documentation](https://roboticshardwaresolutions.github.io/BareMetal-PLCs-Vault/)

## Firmaware
### Cloning source code

```sh
git clone --recursive https://github.com/RoboticsHardwareSolutions/BMPLC_Quick_Project.git
```

### Building firmware

**Necessary tools:**
- cmake
- arm-none-eabi-gcc
- VSCode

**Steps:**
- Open project in VSCode
- Install all recommended extensions
- In root cmake file, set the `BMPLC_M` (by default), `BMPLC_L`, or `BMPLC_XL` variable to the desired hardware
- Build cmake project
- Plug in the BMPLC to your computer by USB
- Start debugging ![alt text](/documentation/images/debug_vscode.png)
    - *Launch jlink* - Use this option to start a debugging session with J-Link when the target device is connected directly to your computer.
    - *Attach jlink* - Use this option to attach the debugger to an already running target device using J-Link. 
    - *Launch Remote jlink* - Use this option to start a remote debugging session with J-Link. This is useful when the target device is connected to a remote machine or when you want to debug over the network.
    - *Attach Remote jlink* - Use this option to attach the debugger to an already running target device using J-Link over the network.

**Remote debugging**
If you need to debug a target device that is not directly connected to your computer, you can use the remote debugging options. Make sure the target device is properly configured for remote debugging and accessible over the network:
On remote system, run the J-Link GDB Server with the appropriate parameters to allow remote connections.
```sh
./JLinkRemoteServer -nogui -select usb=772440171 -USB -device STM32F103RE -endian little -speed 4000 -if swd -rtos GDBServer/RTOSPlugin_FreeRTOS.so
```
Use the `-device STM32F103RE` for BMPLC_M or `-device STM32F767ZG` for BMPLC_L and BMPLC_XL.

Then, in VSCode, select the "Launch Remote jlink" or "Attach Remote jlink" option and provide the necessary connection details (IP address and port number) to connect to the remote J-Link GDB Server.

### Directory `core`
Detailed file-by-file description is available in [core/README.md](core/README.md).

### Features
**RTT CLI**
After launching the debugging session, you can view the RTT log in the "RTT Viewer" tab in VSCode. This allows you to see real-time logs and debug messages from your application.
![alt text](/documentation/images/rtt_vscode.png)

You can use the RTT CLI without vscode by using the `JLinkRTTClient` tool. This tool allows you to interact with the RTT log directly from the command line. You can use it to send commands, view logs, and perform other debugging tasks.
![alt text](/documentation/images/rtt_by_jlink.png)

**Commands:**
- `?` - List all available commands
- `uptime` - shows the uptime of the system
- `free` - shows the amount of free memory available in the system
- `log` - shows and set log level
- `reset` - resets the system
- `uid` - shows the unique identifier of the system
- `top` - shows the top tasks running in the system
- `can_open`:
  - `-f <id>`: Add a CAN ID to the filter list
  - `-e <id>`: Remove a CAN ID from the filter list
  - `-c`: Clear the filter list
  - `-l`: List all CAN IDs in the filter list
  - `-s <id>`: Send a CAN package with the specified ID
  - `-m`: Show this manual
- `usb_bridge`:
  - `-rs232`: Add/Remove a USB RS232 bridge
  - `-rs485`: Add/Remove a USB RS485 bridge
- `mem_test` - performs a memory test
- `log_save_test` - performs a log save test

Example of using the `?` command: ![alt text](/documentation/images/log_help.png)


### Creating a new application
1. Create a new folder in the project
2. Create a new CMakeLists.txt file in the folder with the following content:
```cmake
cmake_minimum_required(VERSION 3.24)
project(new_app C)
set(CMAKE_C_STANDARD 11)

add_library(${PROJECT_NAME} STATIC new_app.c) # Replace `new_app.c` with your source file

target_include_directories(
        ${PROJECT_NAME} PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
) # Include the current directory for the new app

target_link_libraries(
        ${PROJECT_NAME}
        PRIVATE
        rhs
        rhs_hal
        RTT
) # Link against the necessary libraries (serial, can, can_open, notification, etc.)

service(new_app "new_app" 1024)
``` 
`service(new_app "new_app" 1024)` registers the new application as a service with a stack size of 1024 bytes. You can adjust the stack size as needed.
First parameter is the name of the service (this is infinite body of your service), second is the name of the application, and third is the stack size.

3. Create a new source file in the same folder with the same name as the project (e.g., `new_app.c`) and implement your application logic.
```c
#include "rhs.h"
#include "rhs_hal.h"

#define TAG "new_app"

struct NewApp
{
    RHSMutex*  mutex;
    // Add other members as needed
};

NewApp* app_alloc(void)
{
    NewApp* app   = malloc(sizeof(NewApp)); // Allocate memory for the application structure
    app->mutex = rhs_mutex_alloc(RHSMutexTypeNormal); // Allocate a mutex for synchronization
    return app;
}

int32_t new_app(void* context)
{
    NewApp* app = app_alloc();

    // Example: Log a message
    RHS_LOG_I(TAG, "Hello from new_app!");

    for (;;)
    {
        // Your application logic here
        
        // Sleep for a while to avoid busy-waiting
        rhs_delay(1000);
    }
}
```

4. Use tools of rhs_core for your application logic:
   - `RHS_LOG_I(TAG, "message")` - Logs an informational message.
   - `rhs_delay(ms)` - Delays the execution for a specified number of milliseconds.
   - `rhs_mutex`, `rhs_semaphore`, `rhs_queue` etc. - Use these for synchronization and communication between tasks. See the [RHS core documentation](/thirdparty/rhs/README.md) for more details on these tools.
5. Now you can build the project, run your new application on the BMPLC hardware and see it in action by using in RTT `top` command.

### Creating tests
To create tests for your application, you can follow these steps:
1. Create a new folder in the project for your tests.
2. Create a new CMakeLists.txt file in the folder with the following content:
```cmake
# Standard CMake file for new library

# in the end of the file
start_up(new_test_start_up)
```
3. Create a new source file in the same folder with the same name as the project (e.g., `new_test.c`) and implement your test logic.
```c
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <stdint.h>
#include "rhs.h"
#include "rhs_hal.h"

#define TAG "new_test"

void new_test(char* args, void* context) 
{
    // This function will be called when the "new_test" command is executed in the CLI
    // You can use the args parameter to get the arguments passed to the command
    if (args == NULL || strlen(args) == 0)
    {
        RHS_LOG_E(TAG, "No arguments provided for new_test");
        return;
    }

    // Example: Log the received arguments
    RHS_LOG_I(TAG, "Running new_test with args: %s", args);
}

void new_test_start_up(void) // This function add callback for your test to CLI
{
    cli_add_command("new_test", new_test, NULL);
}
```

### Creating HIL tests
Device tests (above) only exercise on-device logic reachable from the RTT CLI. **HIL
(Hardware-in-the-Loop) tests** are for anything that needs the physical test bench —
toggling a PLC's inputs, reading back its outputs/keys, powering a board on/off,
driving CAN/RS232/RS485/RS422 — via the `testbench/io_hub` daemon, with `pytest`
driving both the bench and the board (over RTT, via `bmlab-toolkit`) from the host.

**Layout:** each HIL test gets its own folder under `user_tests/<name>/` with two
subfolders:
- `target/<name>.c` — the on-device side. Same pattern as "Creating tests" above
  (register a `cli_add_command` via a `start_up` hook) but typically without the
  `runit` pass/fail framework, since the bench — not the device — judges pass/fail.
  See `user_tests/io_test/target/io_test.c` for the reference implementation (an `io`
  RTT command to read `IN0-4` and drive `OUT0-4`/`KEY0-4`).
- `testbench/<name>.py` — the host-side `pytest` test. See
  `user_tests/io_test/testbench/io_test.py` for a complete worked example.

**One-time setup:**
- `uv sync` from the repo root (installs `pytest`, `bmlab-toolkit`, `pynng`).
- SEGGER J-Link software installed (`JLinkExe`/`libjlinkarm` on your `PATH`/library
  path) — **run any J-Link tool once interactively first** (e.g. `JLinkExe`) and
  accept whatever activation/firmware-update dialog it shows; `pylink`/`bmlab-toolkit`
  calls block silently waiting on that same dialog otherwise, which looks exactly
  like a hang.
- The bench wired up per `testbench/testbench.toml` (see `testbench/io_hub/README.md`
  for the Modbus/USB-port layout) and built once: `cmake --build
  testbench/io_hub/build --target testbench`.

**Fixtures** (root `conftest.py` — read it for full details/scopes):

| Fixture | Scope | Gives you |
|---|---|---|
| `io_config` | session | resolved `PLC_TYPE`/`JLINK_SERIAL`/`MCU`/paths from env vars + `testbench.toml` |
| `io_hub_daemon` | session | the running `io_hub` daemon (started/stopped for you; reused if one's already up) |
| `tb_client` | session | `TestbenchClient` — IPC read/write of the bench's Modbus coils/bits |
| `tb_labels` | session | `TestbenchLabels` — label ⟷ bit/coil address lookup from `testbench.toml` |
| `plc_power` | module | powers on + USB-enables the PLC under test before your tests, off after |
| `plc` | module | flashes (if `IO_TEST_BIN` set) + connects RTT, yields a `PlcRtt` (`run`/`read_inputs`/`set_out`/`set_key`); resets pins + disconnects after |

Never talk to the bench or the daemon any other way (no shelling out to the
`testbench` CLI, no raw Modbus) — `tb_client`/`tb_labels` are the only supported
path, and the daemon is the only process allowed to hold the bench's serial port.

**Minimal example** (`user_tests/<name>/testbench/<name>.py`):
```python
import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("PLC_TYPE"),
    reason="HIL tests require hardware: set PLC_TYPE=BMPLC_M|BMPLC_XL",
)

def test_out0_reaches_bench(plc, tb_client, tb_labels, io_config):
    plc.set_out(0, True)
    bits = tb_client.get_inputs()["bits"]
    assert tb_labels.decode_inputs(bits)[f"PLC_{io_config.short}_OUT0"] is True
    plc.set_out(0, False)
```
For dynamic, per-pin parametrization derived from `testbench.toml` (rather than
hardcoding pin numbers), see `pytest_generate_tests` in
`user_tests/io_test/testbench/io_test.py` — `pytest.mark.parametrize` can't read
fixtures, so pin discovery there is done again, independently, at collection time.

**Running:**
```sh
# plain `pytest` with no PLC_TYPE set just collects and skips every HIL test, touching nothing
uv run pytest

# a real run against hardware
PLC_TYPE=BMPLC_M IO_TEST_BIN=cmake-build-debug/bmplc.bin \
  uv run pytest user_tests/io_test/testbench/ -v
```
Env vars: `PLC_TYPE` (`BMPLC_M`|`BMPLC_XL`, required), `JLINK_SERIAL`/`MCU` (override
`testbench.toml`'s `[targets.*]`, needed when the toml only has a placeholder),
`IO_TEST_BIN` (firmware to flash first; omit to test whatever's already on the
board), `IO_TEST_CONFIG` (alternate `testbench.toml` path), `IO_TEST_NO_POWER` (skip
the power-on/off step, e.g. if the board is already powered some other way).
