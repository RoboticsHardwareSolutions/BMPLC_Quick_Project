## Context and Build
- The compilation base (flags, HAL includes) is located in `build/compile_commands.json` or
  `cmake-build-debug/compile_commands.json`. Read it if necessary.

## External Libraries
The following directories inside `thirdparty/` contain external third-party libraries and code. 
Do not read, search, or analyze them unless explicitly requested by the user:
  - `thirdparty/freertos/`
  - `thirdparty/mlib/`
  - `thirdparty/mongoose/`
  - `thirdparty/stm32f1_cmsis/`
  - `thirdparty/stm32f1_hal/`
  - `thirdparty/stm32f7_cmsis/`
  - `thirdparty/stm32f7_hal/`
  - `thirdparty/stm32g0_cmsis/`
  - `thirdparty/stm32g0_hal/`
  - `thirdparty/tinyusb/`
  

## Directory Structure with files
- When analyzing the project structure, look only in the following directories:
```text
.
├── ./CHANGELOG.md
├── ./CMakeLists.txt
├── ./README.md
├── ./STM32F103RETX_FLASH.ld
├── ./STM32F765.svd
├── ./STM32F765ZGTX_FLASH.ld
├── ./STM32G0B1.svd
├── ./STM32G0B1KCUX_FLASH.ld
├── ./core
│   ├── ./core/README.md
│   ├── ./core/inc
│   │   ├── ./core/inc/FreeRTOSConfig.h
│   │   ├── ./core/inc/co_config_custom.h
│   │   ├── ./core/inc/f1
│   │   │   ├── ./core/inc/f1/netif
│   │   │   │   └── ./core/inc/f1/netif/ethernet.h
│   │   │   ├── ./core/inc/f1/stm32f1xx_hal_conf.h
│   │   │   └── ./core/inc/f1/tusb_config.h
│   │   ├── ./core/inc/f7
│   │   │   └── ./core/inc/f7/stm32f7xx_hal_conf.h
│   │   ├── ./core/inc/g0
│   │   │   ├── ./core/inc/g0/netif
│   │   │   │   └── ./core/inc/g0/netif/ethernet.h
│   │   │   ├── ./core/inc/g0/stm32g0xx_hal_conf.h
│   │   │   └── ./core/inc/g0/tusb_config.h
│   └── ./core/src
│       ├── ./core/src/f1
│       │   ├── ./core/src/f1/stm32f1xx_hal_msp.c
│       │   ├── ./core/src/f1/stm32f1xx_hal_timebase_tim.c
│       │   └── ./core/src/f1/system_stm32f1xx.c
│       ├── ./core/src/f7
│       │   ├── ./core/src/f7/stm32f7xx_hal_timebase_tim.c
│       │   └── ./core/src/f7/system_stm32f7xx.c
│       ├── ./core/src/g0
│       │   ├── ./core/src/g0/stm32g0xx_hal_msp.c
│       │   └── ./core/src/g0/system_stm32g0xx.c
│       ├── ./core/src/syscalls.c
│       └── ./core/src/sysmem.c
├── ./documentation
│   ├── ./documentation/hil_stand.md
│   └── ./documentation/images
│       ├── ./documentation/images/hil_satnd.jpg
│       ├── ./documentation/images/log_help.png
│       ├── ./documentation/images/rtt_by_jlink.png
├── ./main.c
├── ./project_struct.txt
├── ./pyproject.toml
├── ./stm32f103.svd
├── ./testbench
│   ├── ./testbench/99-usb-serial.rules
│   ├── ./testbench/README.md
│   ├── ./testbench/cli.py
│   ├── ./testbench/iface.py
│   ├── ./testbench/io.py
│   ├── ./testbench/pyproject.toml
│   ├── ./testbench/testbench.toml
│   └── ./testbench/uv.lock
├── ./thirdparty
│   ├── ./thirdparty/CMakeLists.txt
│   ├── ./thirdparty/RTT
│   │   ├── ./thirdparty/RTT/Config
│   │   │   └── ./thirdparty/RTT/Config/SEGGER_RTT_Conf.h
│   │   ├── ./thirdparty/RTT/Examples
│   │   │   ├── ./thirdparty/RTT/Examples/Main_RTT_InputEchoApp.c
│   │   │   ├── ./thirdparty/RTT/Examples/Main_RTT_MenuApp.c
│   │   │   ├── ./thirdparty/RTT/Examples/Main_RTT_PrintfTest.c
│   │   │   └── ./thirdparty/RTT/Examples/Main_RTT_SpeedTestApp.c
│   │   ├── ./thirdparty/RTT/LICENSE.md
│   │   ├── ./thirdparty/RTT/README.md
│   │   ├── ./thirdparty/RTT/RTT
│   │   │   ├── ./thirdparty/RTT/RTT/SEGGER_RTT.c
│   │   │   ├── ./thirdparty/RTT/RTT/SEGGER_RTT.h
│   │   │   ├── ./thirdparty/RTT/RTT/SEGGER_RTT_ASM_ARMv7M.S
│   │   │   └── ./thirdparty/RTT/RTT/SEGGER_RTT_printf.c
│   │   └── ./thirdparty/RTT/Syscalls
│   │       ├── ./thirdparty/RTT/Syscalls/SEGGER_RTT_Syscalls_GCC.c
│   │       ├── ./thirdparty/RTT/Syscalls/SEGGER_RTT_Syscalls_IAR.c
│   │       ├── ./thirdparty/RTT/Syscalls/SEGGER_RTT_Syscalls_KEIL.c
│   │       └── ./thirdparty/RTT/Syscalls/SEGGER_RTT_Syscalls_SES.c
│   ├── ./thirdparty/co_stack
│   │   ├── ./thirdparty/co_stack/CMakeLists.txt
│   │   ├── ./thirdparty/co_stack/README.md
│   │   ├── ./thirdparty/co_stack/include
│   │   │   ├── ./thirdparty/co_stack/include/applicfg.h
│   │   │   ├── ./thirdparty/co_stack/include/can_driver.h
│   │   │   ├── ./thirdparty/co_stack/include/co_can.h
│   │   │   ├── ./thirdparty/co_stack/include/config.h
│   │   │   ├── ./thirdparty/co_stack/include/data.h
│   │   │   ├── ./thirdparty/co_stack/include/dcf.h
│   │   │   ├── ./thirdparty/co_stack/include/def.h
│   │   │   ├── ./thirdparty/co_stack/include/emcy.h
│   │   │   ├── ./thirdparty/co_stack/include/lifegrd.h
│   │   │   ├── ./thirdparty/co_stack/include/lss.h
│   │   │   ├── ./thirdparty/co_stack/include/nmtMaster.h
│   │   │   ├── ./thirdparty/co_stack/include/nmtSlave.h
│   │   │   ├── ./thirdparty/co_stack/include/objacces.h
│   │   │   ├── ./thirdparty/co_stack/include/objaccessinternal.h
│   │   │   ├── ./thirdparty/co_stack/include/objdictdef.h
│   │   │   ├── ./thirdparty/co_stack/include/pdo.h
│   │   │   ├── ./thirdparty/co_stack/include/sdo.h
│   │   │   ├── ./thirdparty/co_stack/include/states.h
│   │   │   ├── ./thirdparty/co_stack/include/sync.h
│   │   │   ├── ./thirdparty/co_stack/include/sysdep.h
│   │   │   ├── ./thirdparty/co_stack/include/timer.h
│   │   │   ├── ./thirdparty/co_stack/include/timers_driver.h
│   │   │   └── ./thirdparty/co_stack/include/timerscfg.h
│   │   └── ./thirdparty/co_stack/src
│   │       ├── ./thirdparty/co_stack/src/dcf.c
│   │       ├── ./thirdparty/co_stack/src/emcy.c
│   │       ├── ./thirdparty/co_stack/src/lifegrd.c
│   │       ├── ./thirdparty/co_stack/src/lss.c
│   │       ├── ./thirdparty/co_stack/src/nmtMaster.c
│   │       ├── ./thirdparty/co_stack/src/nmtSlave.c
│   │       ├── ./thirdparty/co_stack/src/objacces.c
│   │       ├── ./thirdparty/co_stack/src/pdo.c
│   │       ├── ./thirdparty/co_stack/src/sdo.c
│   │       ├── ./thirdparty/co_stack/src/states.c
│   │       ├── ./thirdparty/co_stack/src/symbols.c
│   │       ├── ./thirdparty/co_stack/src/sync.c
│   │       └── ./thirdparty/co_stack/src/timer.c
│   ├── ./thirdparty/rcan
│   │   ├── ./thirdparty/rcan/CMakeLists.txt
│   │   ├── ./thirdparty/rcan/Dockerfile
│   │   ├── ./thirdparty/rcan/README.md
│   │   ├── ./thirdparty/rcan/can
│   │   │   ├── ./thirdparty/rcan/can/bx_can.c
│   │   │   ├── ./thirdparty/rcan/can/bx_can.h
│   │   │   ├── ./thirdparty/rcan/can/bx_canfd.c
│   │   │   ├── ./thirdparty/rcan/can/bx_canfd.h
│   │   │   ├── ./thirdparty/rcan/can/u_can.c
│   │   │   ├── ./thirdparty/rcan/can/u_can.h
│   │   │   └── ./thirdparty/rcan/can/u_can_urls.h
│   │   ├── ./thirdparty/rcan/doc
│   │   │   └── ./thirdparty/rcan/doc/r.png
│   │   ├── ./thirdparty/rcan/example
│   │   │   └── ./thirdparty/rcan/example/virtual_bus
│   │   │       ├── ./thirdparty/rcan/example/virtual_bus/CMakeLists.txt
│   │   │       └── ./thirdparty/rcan/example/virtual_bus/main.c
│   │   ├── ./thirdparty/rcan/rcan.c
│   │   ├── ./thirdparty/rcan/rcan.h
│   │   ├── ./thirdparty/rcan/rcan_def.h
│   │   ├── ./thirdparty/rcan/rcan_filter.c
│   │   ├── ./thirdparty/rcan/rcan_filter.h
│   │   ├── ./thirdparty/rcan/rcan_timing.c
│   │   ├── ./thirdparty/rcan/rcan_timing.h
│   │   ├── ./thirdparty/rcan/rcmake_macros
│   │   │   ├── ./thirdparty/rcan/rcmake_macros/README.md
│   │   │   ├── ./thirdparty/rcan/rcmake_macros/clang.cmake
│   │   │   └── ./thirdparty/rcan/rcmake_macros/rcmake_macros.cmake
│   │   ├── ./thirdparty/rcan/rnode
│   │   ├── ./thirdparty/rcan/test
│   │   │   ├── ./thirdparty/rcan/test/README.md
│   │   │   ├── ./thirdparty/rcan/test/hardware_macos.c
│   │   │   ├── ./thirdparty/rcan/test/hardware_macos.h
│   │   │   ├── ./thirdparty/rcan/test/hardware_unix.c
│   │   │   ├── ./thirdparty/rcan/test/hardware_unix.h
│   │   │   ├── ./thirdparty/rcan/test/runit
│   │   │   ├── ./thirdparty/rcan/test/test.c
│   │   │   ├── ./thirdparty/rcan/test/test.h
│   │   │   ├── ./thirdparty/rcan/test/virtual_bus.c
│   │   │   ├── ./thirdparty/rcan/test/virtual_bus.h
│   │   │   ├── ./thirdparty/rcan/test/virtual_can.c
│   │   │   └── ./thirdparty/rcan/test/virtual_can.h
│   │   ├── ./thirdparty/rcan/thirdparty
│   │   │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux
│   │   │   │   └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src
│   │   │   │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/Makefile
│   │   │   │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/Makefile_latest.mk
│   │   │   │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/changelog.md
│   │   │   │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/include
│   │   │   │       │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/include/PCANBasic.cs
│   │   │   │       │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/include/PCANBasic.h
│   │   │   │       │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/include/PCANBasic.py
│   │   │   │       │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/include/PCANBasic.vb
│   │   │   │       │   └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/include/PCANBasicCLR.h
│   │   │   │       └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/libpcanbasic.c
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/libpcanbasic.def
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan
│   │   │   │           │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/driver
│   │   │   │           │   │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/driver/pcan.h
│   │   │   │           │   │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/driver/pcanfd.h
│   │   │   │           │   │   └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/driver/pcanxl.h
│   │   │   │           │   └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/lib
│   │   │   │           │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/lib/libpcanfd.h
│   │   │   │           │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/lib/libpcanxl.h
│   │   │   │           │       └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/lib/src
│   │   │   │           │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/lib/src/libpcanfd.c
│   │   │   │           │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/lib/src/libpcanxl.c
│   │   │   │           │           └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/lib/src/libprivate.h
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcaninfo.c
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcaninfo.h
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcanlog.c
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcanlog.h
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcbcore.c
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcbcore.h
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcbcore_data.h
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcblog.c
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcblog.h
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcbtrace.c
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcbtrace.h
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/resource.h
│   │   │   │           └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/version.h
│   │   │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-mac
│   │   │   │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-mac/PCBUSB.h
│   │   │   │   └── ./thirdparty/rcan/thirdparty/PCAN-Basic-mac/libPCBUSB.0.8.1.dylib
│   │   │   └── ./thirdparty/rcan/thirdparty/PCAN-Basic-windows
│   │   │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-windows/PCANBasic.dll
│   │   │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-windows/PCANBasic.h
│   │   │       └── ./thirdparty/rcan/thirdparty/PCAN-Basic-windows/PCANBasic.lib
│   │   └── ./thirdparty/rcan/tool
│   │       ├── ./thirdparty/rcan/tool/README.md
│   │       ├── ./thirdparty/rcan/tool/entrypoint.sh
│   │       └── ./thirdparty/rcan/tool/run_tests.sh
│   ├── ./thirdparty/rhs
│   │   ├── ./thirdparty/rhs/CHANGELOG.md
│   │   ├── ./thirdparty/rhs/CMakeLists.txt
│   │   ├── ./thirdparty/rhs/README.md
│   │   ├── ./thirdparty/rhs/applications
│   │   │   ├── ./thirdparty/rhs/applications/CMakeLists.txt
│   │   │   ├── ./thirdparty/rhs/applications/services
│   │   │   │   ├── ./thirdparty/rhs/applications/services/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/CMakeLists.txt
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/can_open.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/can_open_cli.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/can_open_ctrl_dev.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/can_open_srv.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/can_open_srv.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/can_open_srv_i.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/od_common_defs.c
│   │   │   │   │   └── ./thirdparty/rhs/applications/services/can_open/od_common_defs.h
│   │   │   │   ├── ./thirdparty/rhs/applications/services/cli
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/cli/CMakeLists.txt
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/cli/cli.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/cli/cli_app.c
│   │   │   │   │   └── ./thirdparty/rhs/applications/services/cli/cli_app.h
│   │   │   │   ├── ./thirdparty/rhs/applications/services/loader
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/loader/CMakeLists.txt
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/loader/loader.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/loader/loader.h
│   │   │   │   │   └── ./thirdparty/rhs/applications/services/loader/loader_i.h
│   │   │   │   ├── ./thirdparty/rhs/applications/services/net
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/CMakeLists.txt
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/README.md
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/eth_net
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/eth_net/CMakeLists.txt
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/eth_net/README.md
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/eth_net/eth_net.c
│   │   │   │   │   │   └── ./thirdparty/rhs/applications/services/net/eth_net/eth_net.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/modbus_tcp
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/modbus_tcp/CMakeLists.txt
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/modbus_tcp/modbus_tcp.c
│   │   │   │   │   │   └── ./thirdparty/rhs/applications/services/net/modbus_tcp/modbus_tcp.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net_i.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net_listeners
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net_listeners/CMakeLists.txt
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net_listeners/net_listeners.c
│   │   │   │   │   │   └── ./thirdparty/rhs/applications/services/net/net_listeners/net_listeners.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net_utils
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net_utils/CMakeLists.txt
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net_utils/net_utils.c
│   │   │   │   │   │   └── ./thirdparty/rhs/applications/services/net/net_utils/net_utils.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/usb_cdc_net
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/usb_cdc_net/CMakeLists.txt
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/usb_cdc_net/README.md
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/usb_cdc_net/tusb_config.h.example
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/usb_cdc_net/usb_cdc_net.c
│   │   │   │   │   │   └── ./thirdparty/rhs/applications/services/net/usb_cdc_net/usb_cdc_net.h
│   │   │   │   │   └── ./thirdparty/rhs/applications/services/net/usb_eth_bridge
│   │   │   │   │       ├── ./thirdparty/rhs/applications/services/net/usb_eth_bridge/CMakeLists.txt
│   │   │   │   │       ├── ./thirdparty/rhs/applications/services/net/usb_eth_bridge/README.md
│   │   │   │   │       ├── ./thirdparty/rhs/applications/services/net/usb_eth_bridge/usb_eth_bridge.c
│   │   │   │   │       └── ./thirdparty/rhs/applications/services/net/usb_eth_bridge/usb_eth_bridge.h
│   │   │   │   ├── ./thirdparty/rhs/applications/services/notification
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/CMakeLists.txt
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/notification.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/notification_app.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/notification_app.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/notification_app_api.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/notification_messages.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/notification_messages.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/notification_messages_notes.c
│   │   │   │   │   └── ./thirdparty/rhs/applications/services/notification/notification_messages_notes.h
│   │   │   │   └── ./thirdparty/rhs/applications/services/usb_serial_bridge
│   │   │   │       ├── ./thirdparty/rhs/applications/services/usb_serial_bridge/CMakeLists.txt
│   │   │   │       ├── ./thirdparty/rhs/applications/services/usb_serial_bridge/usb_serial_bridge.c
│   │   │   │       └── ./thirdparty/rhs/applications/services/usb_serial_bridge/usb_serial_bridge.h
│   │   │   └── ./thirdparty/rhs/applications/tests
│   │   │       ├── ./thirdparty/rhs/applications/tests/CMakeLists.txt
│   │   │       └── ./thirdparty/rhs/applications/tests/rhs_tests
│   │   │           ├── ./thirdparty/rhs/applications/tests/rhs_tests/CMakeLists.txt
│   │   │           ├── ./thirdparty/rhs/applications/tests/rhs_tests/flash_ex_unit_test.c
│   │   │           ├── ./thirdparty/rhs/applications/tests/rhs_tests/memmng_unit_test.c
│   │   │           └── ./thirdparty/rhs/applications/tests/rhs_tests/records_test
│   │   │               ├── ./thirdparty/rhs/applications/tests/rhs_tests/records_test/CMakeLists.txt
│   │   │               └── ./thirdparty/rhs/applications/tests/rhs_tests/records_test/records_test.c
│   │   ├── ./thirdparty/rhs/applications.h
│   │   ├── ./thirdparty/rhs/cmake
│   │   │   ├── ./thirdparty/rhs/cmake/git_sha.cmake
│   │   │   ├── ./thirdparty/rhs/cmake/rhs.cmake
│   │   │   └── ./thirdparty/rhs/cmake/rhs_version.h.in
│   │   ├── ./thirdparty/rhs/core
│   │   │   ├── ./thirdparty/rhs/core/api_lock.h
│   │   │   ├── ./thirdparty/rhs/core/base.h
│   │   │   ├── ./thirdparty/rhs/core/check.c
│   │   │   ├── ./thirdparty/rhs/core/check.h
│   │   │   ├── ./thirdparty/rhs/core/common.h
│   │   │   ├── ./thirdparty/rhs/core/critical.c
│   │   │   ├── ./thirdparty/rhs/core/defines.h
│   │   │   ├── ./thirdparty/rhs/core/event_flag.c
│   │   │   ├── ./thirdparty/rhs/core/event_flag.h
│   │   │   ├── ./thirdparty/rhs/core/kernel.c
│   │   │   ├── ./thirdparty/rhs/core/kernel.h
│   │   │   ├── ./thirdparty/rhs/core/log.c
│   │   │   ├── ./thirdparty/rhs/core/log.h
│   │   │   ├── ./thirdparty/rhs/core/m_cstr_dup.h
│   │   │   ├── ./thirdparty/rhs/core/memmgr.c
│   │   │   ├── ./thirdparty/rhs/core/memmgr.h
│   │   │   ├── ./thirdparty/rhs/core/message_queue.c
│   │   │   ├── ./thirdparty/rhs/core/message_queue.h
│   │   │   ├── ./thirdparty/rhs/core/mutex.c
│   │   │   ├── ./thirdparty/rhs/core/mutex.h
│   │   │   ├── ./thirdparty/rhs/core/record.c
│   │   │   ├── ./thirdparty/rhs/core/record.h
│   │   │   ├── ./thirdparty/rhs/core/semaphore.c
│   │   │   ├── ./thirdparty/rhs/core/semaphore.h
│   │   │   ├── ./thirdparty/rhs/core/stream_buf.c
│   │   │   ├── ./thirdparty/rhs/core/stream_buf.h
│   │   │   ├── ./thirdparty/rhs/core/thread.c
│   │   │   ├── ./thirdparty/rhs/core/thread.h
│   │   │   ├── ./thirdparty/rhs/core/thread_list.c
│   │   │   ├── ./thirdparty/rhs/core/thread_list.h
│   │   │   ├── ./thirdparty/rhs/core/timer.c
│   │   │   └── ./thirdparty/rhs/core/timer.h
│   │   ├── ./thirdparty/rhs/drivers
│   │   │   ├── ./thirdparty/rhs/drivers/CMakeLists.txt
│   │   │   └── ./thirdparty/rhs/drivers/eeprom
│   │   │       ├── ./thirdparty/rhs/drivers/eeprom/CMakeLists.txt
│   │   │       ├── ./thirdparty/rhs/drivers/eeprom/eeprom.c
│   │   │       └── ./thirdparty/rhs/drivers/eeprom/eeprom.h
│   │   ├── ./thirdparty/rhs/hal
│   │   │   ├── ./thirdparty/rhs/hal/CMakeLists.txt
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal.c
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_can
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_can/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_can/rhs_hal_can.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_can/rhs_hal_can.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_cortex
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_cortex/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_cortex/rhs_hal_cortex.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_cortex/rhs_hal_cortex.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_eth
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_eth/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_eth/rhs_hal_eth.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_eth/rhs_hal_eth.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_flash_ex
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_flash_ex/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_flash_ex/mt25ql128aba
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_flash_ex/mt25ql128aba/CMakeLists.txt
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_flash_ex/mt25ql128aba/mt25ql128aba.c
│   │   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_flash_ex/mt25ql128aba/mt25ql128aba.h
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_flash_ex/rhs_hal_flash_ex.c
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_flash_ex/rhs_hal_flash_ex.h
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_flash_ex/usage_example.md
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_gpio
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_gpio/CMakeLists.txt
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_gpio/rhs_hal_gpio.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_i2c
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_i2c/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_i2c/rhs_hal_i2c.c
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_i2c/rhs_hal_i2c.h
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_i2c/rhs_hal_i2c_config.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_i2c/rhs_hal_i2c_type.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_interrupt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_interrupt/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_interrupt/rhs_hal_interrupt.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_interrupt/rhs_hal_interrupt.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_io
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_io/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_io/rhs_hal_io.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_io/rhs_hal_io.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_power
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_power/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_power/rhs_hal_power.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_power/rhs_hal_power.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_random
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_random/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_random/rhs_hal_random.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_random/rhs_hal_random.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_rtc
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_rtc/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_rtc/rhs_hal_rtc.c
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_rtc/rhs_hal_rtc.h
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_rtc/unixtime
│   │   │   │       ├── ./thirdparty/rhs/hal/rhs_hal_rtc/unixtime/CMakeLists.txt
│   │   │   │       ├── ./thirdparty/rhs/hal/rhs_hal_rtc/unixtime/unixtime.c
│   │   │   │       └── ./thirdparty/rhs/hal/rhs_hal_rtc/unixtime/unixtime.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/internal
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/internal/hal_rs232.c
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/internal/hal_rs232.h
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/internal/hal_rs422.c
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/internal/hal_rs422.h
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/internal/hal_rs485.c
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/internal/hal_rs485.h
│   │   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_serial/internal/rhs_hal_serial_types_i.h
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/rhs_hal_serial.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_serial/rhs_hal_serial.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_speaker
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_speaker/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_speaker/rhs_hal_speaker.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_speaker/rhs_hal_speaker.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb/rhs_hal_usb.c
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb/rhs_hal_usb.h
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb/rhs_hal_usb_cdc.c
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb/rhs_hal_usb_cdc.h
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb/tud_net_dispatch.c
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb/tud_net_dispatch.h
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_usb/usb_descriptors.c
│   │   │   └── ./thirdparty/rhs/hal/rhs_hal_version
│   │   │       ├── ./thirdparty/rhs/hal/rhs_hal_version/CMakeLists.txt
│   │   │       ├── ./thirdparty/rhs/hal/rhs_hal_version/rhs_hal_version.c
│   │   │       └── ./thirdparty/rhs/hal/rhs_hal_version/rhs_hal_version.h
│   │   ├── ./thirdparty/rhs/rhs.c
│   │   └── ./thirdparty/rhs/rhs.h
│   ├── ./thirdparty/rserial
│   │   ├── ./thirdparty/rserial/CMakeLists.txt
│   │   ├── ./thirdparty/rserial/README.md
│   │   ├── ./thirdparty/rserial/rserial.c
│   │   ├── ./thirdparty/rserial/rserial.h
│   │   ├── ./thirdparty/rserial/rserial_def.h
│   │   ├── ./thirdparty/rserial/test
│   │   │   ├── ./thirdparty/rserial/test/socatfortests.sh
│   │   │   └── ./thirdparty/rserial/test/test.c
│   │   └── ./thirdparty/rserial/utils
│   │       ├── ./thirdparty/rserial/utils/rserial_term.c
│   │       ├── ./thirdparty/rserial/utils/screen.c
│   │       ├── ./thirdparty/rserial/utils/screen.h
│   │       ├── ./thirdparty/rserial/utils/tty.c
│   │       └── ./thirdparty/rserial/utils/tty.h
│   ├── ./thirdparty/rtimer
│   │   ├── ./thirdparty/rtimer/CMakeLists.txt
│   │   ├── ./thirdparty/rtimer/README.md
│   │   ├── ./thirdparty/rtimer/rtimer.c
│   │   ├── ./thirdparty/rtimer/rtimer.h
│   │   ├── ./thirdparty/rtimer/rtimer_def.h
│   │   └── ./thirdparty/rtimer/test
│   │       └── ./thirdparty/rtimer/test/test.c
│   ├── ./thirdparty/runit
│   │   ├── ./thirdparty/runit/CMakeLists.txt
│   │   ├── ./thirdparty/runit/README.md
│   │   ├── ./thirdparty/runit/compiler_flags.cmake
│   │   ├── ./thirdparty/runit/examples
│   │   │   └── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/CMakeLists.txt
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/JLinkRTTViewer.png
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/Ozone.png
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/README.md
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/STM32F103.svd
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/STM32F103RETX_FLASH.ld
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/main.c
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/startup_stm32f103xe.s
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/stm32f103xe.h
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/syscalls.c
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/sysinit.c
│   │   │       └── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/system_stm32f1xx.h
│   │   ├── ./thirdparty/runit/src
│   │   │   ├── ./thirdparty/runit/src/runit.c
│   │   │   └── ./thirdparty/runit/src/runit.h
│   │   └── ./thirdparty/runit/tst
│   │       └── ./thirdparty/runit/tst/selftest.c
├── ./toolchains
│   ├── ./toolchains/g0b1.cmake
│   ├── ./toolchains/plc_l.cmake
│   ├── ./toolchains/plc_m.cmake
│   └── ./toolchains/plc_xl.cmake
├── ./user_apps
│   ├── ./user_apps/CMakeLists.txt
│   ├── ./user_apps/cdc_net_hello_rhs
│   │   ├── ./user_apps/cdc_net_hello_rhs/CMakeLists.txt
│   │   ├── ./user_apps/cdc_net_hello_rhs/cdc_net_hello_rhs.c
│   │   └── ./user_apps/cdc_net_hello_rhs/dist
│   │       └── ./user_apps/cdc_net_hello_rhs/dist/index.html
│   └── ./user_apps/eth_net_hello_rhs
│       ├── ./user_apps/eth_net_hello_rhs/CMakeLists.txt
│       ├── ./user_apps/eth_net_hello_rhs/dist
│       │   └── ./user_apps/eth_net_hello_rhs/dist/index.html
│       └── ./user_apps/eth_net_hello_rhs/eth_net_hello_rhs.c
├── ./user_tests
│   ├── ./user_tests/CMakeLists.txt
│   └── ./user_tests/eeprom_test
│       ├── ./user_tests/eeprom_test/CMakeLists.txt
│       └── ./user_tests/eeprom_test/eeprom_test.c
└── ./uv.lock.
├── ./CHANGELOG.md
├── ./CMakeLists.txt
├── ./README.md
├── ./STM32F103RETX_FLASH.ld
├── ./STM32F765.svd
├── ./STM32F765ZGTX_FLASH.ld
├── ./STM32G0B1.svd
├── ./STM32G0B1KCUX_FLASH.ld
├── ./core
│   ├── ./core/README.md
│   ├── ./core/inc
│   │   ├── ./core/inc/FreeRTOSConfig.h
│   │   ├── ./core/inc/co_config_custom.h
│   │   ├── ./core/inc/f1
│   │   │   ├── ./core/inc/f1/netif
│   │   │   │   └── ./core/inc/f1/netif/ethernet.h
│   │   │   ├── ./core/inc/f1/stm32f1xx_hal_conf.h
│   │   │   └── ./core/inc/f1/tusb_config.h
│   │   ├── ./core/inc/f7
│   │   │   └── ./core/inc/f7/stm32f7xx_hal_conf.h
│   │   ├── ./core/inc/g0
│   │   │   ├── ./core/inc/g0/netif
│   │   │   │   └── ./core/inc/g0/netif/ethernet.h
│   │   │   ├── ./core/inc/g0/stm32g0xx_hal_conf.h
│   │   │   └── ./core/inc/g0/tusb_config.h
│   └── ./core/src
│       ├── ./core/src/f1
│       │   ├── ./core/src/f1/stm32f1xx_hal_msp.c
│       │   ├── ./core/src/f1/stm32f1xx_hal_timebase_tim.c
│       │   └── ./core/src/f1/system_stm32f1xx.c
│       ├── ./core/src/f7
│       │   ├── ./core/src/f7/stm32f7xx_hal_timebase_tim.c
│       │   └── ./core/src/f7/system_stm32f7xx.c
│       ├── ./core/src/g0
│       │   ├── ./core/src/g0/stm32g0xx_hal_msp.c
│       │   └── ./core/src/g0/system_stm32g0xx.c
│       ├── ./core/src/syscalls.c
│       └── ./core/src/sysmem.c
├── ./documentation
│   ├── ./documentation/hil_stand.md
│   └── ./documentation/images
│       ├── ./documentation/images/hil_satnd.jpg
│       ├── ./documentation/images/log_help.png
│       ├── ./documentation/images/rtt_by_jlink.png
├── ./main.c
├── ./project_struct.txt
├── ./pyproject.toml
├── ./stm32f103.svd
├── ./testbench
│   ├── ./testbench/99-usb-serial.rules
│   ├── ./testbench/README.md
│   ├── ./testbench/cli.py
│   ├── ./testbench/iface.py
│   ├── ./testbench/io.py
│   ├── ./testbench/pyproject.toml
│   ├── ./testbench/testbench.toml
│   └── ./testbench/uv.lock
├── ./thirdparty
│   ├── ./thirdparty/CMakeLists.txt
│   ├── ./thirdparty/RTT
│   │   ├── ./thirdparty/RTT/Config
│   │   │   └── ./thirdparty/RTT/Config/SEGGER_RTT_Conf.h
│   │   ├── ./thirdparty/RTT/Examples
│   │   │   ├── ./thirdparty/RTT/Examples/Main_RTT_InputEchoApp.c
│   │   │   ├── ./thirdparty/RTT/Examples/Main_RTT_MenuApp.c
│   │   │   ├── ./thirdparty/RTT/Examples/Main_RTT_PrintfTest.c
│   │   │   └── ./thirdparty/RTT/Examples/Main_RTT_SpeedTestApp.c
│   │   ├── ./thirdparty/RTT/LICENSE.md
│   │   ├── ./thirdparty/RTT/README.md
│   │   ├── ./thirdparty/RTT/RTT
│   │   │   ├── ./thirdparty/RTT/RTT/SEGGER_RTT.c
│   │   │   ├── ./thirdparty/RTT/RTT/SEGGER_RTT.h
│   │   │   ├── ./thirdparty/RTT/RTT/SEGGER_RTT_ASM_ARMv7M.S
│   │   │   └── ./thirdparty/RTT/RTT/SEGGER_RTT_printf.c
│   │   └── ./thirdparty/RTT/Syscalls
│   │       ├── ./thirdparty/RTT/Syscalls/SEGGER_RTT_Syscalls_GCC.c
│   │       ├── ./thirdparty/RTT/Syscalls/SEGGER_RTT_Syscalls_IAR.c
│   │       ├── ./thirdparty/RTT/Syscalls/SEGGER_RTT_Syscalls_KEIL.c
│   │       └── ./thirdparty/RTT/Syscalls/SEGGER_RTT_Syscalls_SES.c
│   ├── ./thirdparty/co_stack
│   │   ├── ./thirdparty/co_stack/CMakeLists.txt
│   │   ├── ./thirdparty/co_stack/README.md
│   │   ├── ./thirdparty/co_stack/include
│   │   │   ├── ./thirdparty/co_stack/include/applicfg.h
│   │   │   ├── ./thirdparty/co_stack/include/can_driver.h
│   │   │   ├── ./thirdparty/co_stack/include/co_can.h
│   │   │   ├── ./thirdparty/co_stack/include/config.h
│   │   │   ├── ./thirdparty/co_stack/include/data.h
│   │   │   ├── ./thirdparty/co_stack/include/dcf.h
│   │   │   ├── ./thirdparty/co_stack/include/def.h
│   │   │   ├── ./thirdparty/co_stack/include/emcy.h
│   │   │   ├── ./thirdparty/co_stack/include/lifegrd.h
│   │   │   ├── ./thirdparty/co_stack/include/lss.h
│   │   │   ├── ./thirdparty/co_stack/include/nmtMaster.h
│   │   │   ├── ./thirdparty/co_stack/include/nmtSlave.h
│   │   │   ├── ./thirdparty/co_stack/include/objacces.h
│   │   │   ├── ./thirdparty/co_stack/include/objaccessinternal.h
│   │   │   ├── ./thirdparty/co_stack/include/objdictdef.h
│   │   │   ├── ./thirdparty/co_stack/include/pdo.h
│   │   │   ├── ./thirdparty/co_stack/include/sdo.h
│   │   │   ├── ./thirdparty/co_stack/include/states.h
│   │   │   ├── ./thirdparty/co_stack/include/sync.h
│   │   │   ├── ./thirdparty/co_stack/include/sysdep.h
│   │   │   ├── ./thirdparty/co_stack/include/timer.h
│   │   │   ├── ./thirdparty/co_stack/include/timers_driver.h
│   │   │   └── ./thirdparty/co_stack/include/timerscfg.h
│   │   └── ./thirdparty/co_stack/src
│   │       ├── ./thirdparty/co_stack/src/dcf.c
│   │       ├── ./thirdparty/co_stack/src/emcy.c
│   │       ├── ./thirdparty/co_stack/src/lifegrd.c
│   │       ├── ./thirdparty/co_stack/src/lss.c
│   │       ├── ./thirdparty/co_stack/src/nmtMaster.c
│   │       ├── ./thirdparty/co_stack/src/nmtSlave.c
│   │       ├── ./thirdparty/co_stack/src/objacces.c
│   │       ├── ./thirdparty/co_stack/src/pdo.c
│   │       ├── ./thirdparty/co_stack/src/sdo.c
│   │       ├── ./thirdparty/co_stack/src/states.c
│   │       ├── ./thirdparty/co_stack/src/symbols.c
│   │       ├── ./thirdparty/co_stack/src/sync.c
│   │       └── ./thirdparty/co_stack/src/timer.c
│   ├── ./thirdparty/rcan
│   │   ├── ./thirdparty/rcan/CMakeLists.txt
│   │   ├── ./thirdparty/rcan/Dockerfile
│   │   ├── ./thirdparty/rcan/README.md
│   │   ├── ./thirdparty/rcan/can
│   │   │   ├── ./thirdparty/rcan/can/bx_can.c
│   │   │   ├── ./thirdparty/rcan/can/bx_can.h
│   │   │   ├── ./thirdparty/rcan/can/bx_canfd.c
│   │   │   ├── ./thirdparty/rcan/can/bx_canfd.h
│   │   │   ├── ./thirdparty/rcan/can/u_can.c
│   │   │   ├── ./thirdparty/rcan/can/u_can.h
│   │   │   └── ./thirdparty/rcan/can/u_can_urls.h
│   │   ├── ./thirdparty/rcan/doc
│   │   │   └── ./thirdparty/rcan/doc/r.png
│   │   ├── ./thirdparty/rcan/example
│   │   │   └── ./thirdparty/rcan/example/virtual_bus
│   │   │       ├── ./thirdparty/rcan/example/virtual_bus/CMakeLists.txt
│   │   │       └── ./thirdparty/rcan/example/virtual_bus/main.c
│   │   ├── ./thirdparty/rcan/rcan.c
│   │   ├── ./thirdparty/rcan/rcan.h
│   │   ├── ./thirdparty/rcan/rcan_def.h
│   │   ├── ./thirdparty/rcan/rcan_filter.c
│   │   ├── ./thirdparty/rcan/rcan_filter.h
│   │   ├── ./thirdparty/rcan/rcan_timing.c
│   │   ├── ./thirdparty/rcan/rcan_timing.h
│   │   ├── ./thirdparty/rcan/rcmake_macros
│   │   │   ├── ./thirdparty/rcan/rcmake_macros/README.md
│   │   │   ├── ./thirdparty/rcan/rcmake_macros/clang.cmake
│   │   │   └── ./thirdparty/rcan/rcmake_macros/rcmake_macros.cmake
│   │   ├── ./thirdparty/rcan/rnode
│   │   ├── ./thirdparty/rcan/test
│   │   │   ├── ./thirdparty/rcan/test/README.md
│   │   │   ├── ./thirdparty/rcan/test/hardware_macos.c
│   │   │   ├── ./thirdparty/rcan/test/hardware_macos.h
│   │   │   ├── ./thirdparty/rcan/test/hardware_unix.c
│   │   │   ├── ./thirdparty/rcan/test/hardware_unix.h
│   │   │   ├── ./thirdparty/rcan/test/runit
│   │   │   ├── ./thirdparty/rcan/test/test.c
│   │   │   ├── ./thirdparty/rcan/test/test.h
│   │   │   ├── ./thirdparty/rcan/test/virtual_bus.c
│   │   │   ├── ./thirdparty/rcan/test/virtual_bus.h
│   │   │   ├── ./thirdparty/rcan/test/virtual_can.c
│   │   │   └── ./thirdparty/rcan/test/virtual_can.h
│   │   ├── ./thirdparty/rcan/thirdparty
│   │   │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux
│   │   │   │   └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src
│   │   │   │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/Makefile
│   │   │   │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/Makefile_latest.mk
│   │   │   │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/changelog.md
│   │   │   │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/include
│   │   │   │       │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/include/PCANBasic.cs
│   │   │   │       │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/include/PCANBasic.h
│   │   │   │       │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/include/PCANBasic.py
│   │   │   │       │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/include/PCANBasic.vb
│   │   │   │       │   └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/include/PCANBasicCLR.h
│   │   │   │       └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/libpcanbasic.c
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/libpcanbasic.def
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan
│   │   │   │           │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/driver
│   │   │   │           │   │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/driver/pcan.h
│   │   │   │           │   │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/driver/pcanfd.h
│   │   │   │           │   │   └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/driver/pcanxl.h
│   │   │   │           │   └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/lib
│   │   │   │           │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/lib/libpcanfd.h
│   │   │   │           │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/lib/libpcanxl.h
│   │   │   │           │       └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/lib/src
│   │   │   │           │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/lib/src/libpcanfd.c
│   │   │   │           │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/lib/src/libpcanxl.c
│   │   │   │           │           └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcan/lib/src/libprivate.h
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcaninfo.c
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcaninfo.h
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcanlog.c
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcanlog.h
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcbcore.c
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcbcore.h
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcbcore_data.h
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcblog.c
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcblog.h
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcbtrace.c
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/pcbtrace.h
│   │   │   │           ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/resource.h
│   │   │   │           └── ./thirdparty/rcan/thirdparty/PCAN-Basic-linux/pcanbasic-src/src/version.h
│   │   │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-mac
│   │   │   │   ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-mac/PCBUSB.h
│   │   │   │   └── ./thirdparty/rcan/thirdparty/PCAN-Basic-mac/libPCBUSB.0.8.1.dylib
│   │   │   └── ./thirdparty/rcan/thirdparty/PCAN-Basic-windows
│   │   │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-windows/PCANBasic.dll
│   │   │       ├── ./thirdparty/rcan/thirdparty/PCAN-Basic-windows/PCANBasic.h
│   │   │       └── ./thirdparty/rcan/thirdparty/PCAN-Basic-windows/PCANBasic.lib
│   │   └── ./thirdparty/rcan/tool
│   │       ├── ./thirdparty/rcan/tool/README.md
│   │       ├── ./thirdparty/rcan/tool/entrypoint.sh
│   │       └── ./thirdparty/rcan/tool/run_tests.sh
│   ├── ./thirdparty/rhs
│   │   ├── ./thirdparty/rhs/CHANGELOG.md
│   │   ├── ./thirdparty/rhs/CMakeLists.txt
│   │   ├── ./thirdparty/rhs/README.md
│   │   ├── ./thirdparty/rhs/applications
│   │   │   ├── ./thirdparty/rhs/applications/CMakeLists.txt
│   │   │   ├── ./thirdparty/rhs/applications/services
│   │   │   │   ├── ./thirdparty/rhs/applications/services/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/CMakeLists.txt
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/can_open.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/can_open_cli.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/can_open_ctrl_dev.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/can_open_srv.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/can_open_srv.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/can_open_srv_i.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/can_open/od_common_defs.c
│   │   │   │   │   └── ./thirdparty/rhs/applications/services/can_open/od_common_defs.h
│   │   │   │   ├── ./thirdparty/rhs/applications/services/cli
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/cli/CMakeLists.txt
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/cli/cli.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/cli/cli_app.c
│   │   │   │   │   └── ./thirdparty/rhs/applications/services/cli/cli_app.h
│   │   │   │   ├── ./thirdparty/rhs/applications/services/loader
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/loader/CMakeLists.txt
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/loader/loader.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/loader/loader.h
│   │   │   │   │   └── ./thirdparty/rhs/applications/services/loader/loader_i.h
│   │   │   │   ├── ./thirdparty/rhs/applications/services/net
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/CMakeLists.txt
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/README.md
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/eth_net
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/eth_net/CMakeLists.txt
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/eth_net/README.md
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/eth_net/eth_net.c
│   │   │   │   │   │   └── ./thirdparty/rhs/applications/services/net/eth_net/eth_net.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/modbus_tcp
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/modbus_tcp/CMakeLists.txt
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/modbus_tcp/modbus_tcp.c
│   │   │   │   │   │   └── ./thirdparty/rhs/applications/services/net/modbus_tcp/modbus_tcp.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net_i.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net_listeners
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net_listeners/CMakeLists.txt
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net_listeners/net_listeners.c
│   │   │   │   │   │   └── ./thirdparty/rhs/applications/services/net/net_listeners/net_listeners.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net_utils
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net_utils/CMakeLists.txt
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/net_utils/net_utils.c
│   │   │   │   │   │   └── ./thirdparty/rhs/applications/services/net/net_utils/net_utils.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/usb_cdc_net
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/usb_cdc_net/CMakeLists.txt
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/usb_cdc_net/README.md
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/usb_cdc_net/tusb_config.h.example
│   │   │   │   │   │   ├── ./thirdparty/rhs/applications/services/net/usb_cdc_net/usb_cdc_net.c
│   │   │   │   │   │   └── ./thirdparty/rhs/applications/services/net/usb_cdc_net/usb_cdc_net.h
│   │   │   │   │   └── ./thirdparty/rhs/applications/services/net/usb_eth_bridge
│   │   │   │   │       ├── ./thirdparty/rhs/applications/services/net/usb_eth_bridge/CMakeLists.txt
│   │   │   │   │       ├── ./thirdparty/rhs/applications/services/net/usb_eth_bridge/README.md
│   │   │   │   │       ├── ./thirdparty/rhs/applications/services/net/usb_eth_bridge/usb_eth_bridge.c
│   │   │   │   │       └── ./thirdparty/rhs/applications/services/net/usb_eth_bridge/usb_eth_bridge.h
│   │   │   │   ├── ./thirdparty/rhs/applications/services/notification
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/CMakeLists.txt
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/notification.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/notification_app.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/notification_app.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/notification_app_api.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/notification_messages.c
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/notification_messages.h
│   │   │   │   │   ├── ./thirdparty/rhs/applications/services/notification/notification_messages_notes.c
│   │   │   │   │   └── ./thirdparty/rhs/applications/services/notification/notification_messages_notes.h
│   │   │   │   └── ./thirdparty/rhs/applications/services/usb_serial_bridge
│   │   │   │       ├── ./thirdparty/rhs/applications/services/usb_serial_bridge/CMakeLists.txt
│   │   │   │       ├── ./thirdparty/rhs/applications/services/usb_serial_bridge/usb_serial_bridge.c
│   │   │   │       └── ./thirdparty/rhs/applications/services/usb_serial_bridge/usb_serial_bridge.h
│   │   │   └── ./thirdparty/rhs/applications/tests
│   │   │       ├── ./thirdparty/rhs/applications/tests/CMakeLists.txt
│   │   │       └── ./thirdparty/rhs/applications/tests/rhs_tests
│   │   │           ├── ./thirdparty/rhs/applications/tests/rhs_tests/CMakeLists.txt
│   │   │           ├── ./thirdparty/rhs/applications/tests/rhs_tests/flash_ex_unit_test.c
│   │   │           ├── ./thirdparty/rhs/applications/tests/rhs_tests/memmng_unit_test.c
│   │   │           └── ./thirdparty/rhs/applications/tests/rhs_tests/records_test
│   │   │               ├── ./thirdparty/rhs/applications/tests/rhs_tests/records_test/CMakeLists.txt
│   │   │               └── ./thirdparty/rhs/applications/tests/rhs_tests/records_test/records_test.c
│   │   ├── ./thirdparty/rhs/applications.h
│   │   ├── ./thirdparty/rhs/cmake
│   │   │   ├── ./thirdparty/rhs/cmake/git_sha.cmake
│   │   │   ├── ./thirdparty/rhs/cmake/rhs.cmake
│   │   │   └── ./thirdparty/rhs/cmake/rhs_version.h.in
│   │   ├── ./thirdparty/rhs/core
│   │   │   ├── ./thirdparty/rhs/core/api_lock.h
│   │   │   ├── ./thirdparty/rhs/core/base.h
│   │   │   ├── ./thirdparty/rhs/core/check.c
│   │   │   ├── ./thirdparty/rhs/core/check.h
│   │   │   ├── ./thirdparty/rhs/core/common.h
│   │   │   ├── ./thirdparty/rhs/core/critical.c
│   │   │   ├── ./thirdparty/rhs/core/defines.h
│   │   │   ├── ./thirdparty/rhs/core/event_flag.c
│   │   │   ├── ./thirdparty/rhs/core/event_flag.h
│   │   │   ├── ./thirdparty/rhs/core/kernel.c
│   │   │   ├── ./thirdparty/rhs/core/kernel.h
│   │   │   ├── ./thirdparty/rhs/core/log.c
│   │   │   ├── ./thirdparty/rhs/core/log.h
│   │   │   ├── ./thirdparty/rhs/core/m_cstr_dup.h
│   │   │   ├── ./thirdparty/rhs/core/memmgr.c
│   │   │   ├── ./thirdparty/rhs/core/memmgr.h
│   │   │   ├── ./thirdparty/rhs/core/message_queue.c
│   │   │   ├── ./thirdparty/rhs/core/message_queue.h
│   │   │   ├── ./thirdparty/rhs/core/mutex.c
│   │   │   ├── ./thirdparty/rhs/core/mutex.h
│   │   │   ├── ./thirdparty/rhs/core/record.c
│   │   │   ├── ./thirdparty/rhs/core/record.h
│   │   │   ├── ./thirdparty/rhs/core/semaphore.c
│   │   │   ├── ./thirdparty/rhs/core/semaphore.h
│   │   │   ├── ./thirdparty/rhs/core/stream_buf.c
│   │   │   ├── ./thirdparty/rhs/core/stream_buf.h
│   │   │   ├── ./thirdparty/rhs/core/thread.c
│   │   │   ├── ./thirdparty/rhs/core/thread.h
│   │   │   ├── ./thirdparty/rhs/core/thread_list.c
│   │   │   ├── ./thirdparty/rhs/core/thread_list.h
│   │   │   ├── ./thirdparty/rhs/core/timer.c
│   │   │   └── ./thirdparty/rhs/core/timer.h
│   │   ├── ./thirdparty/rhs/drivers
│   │   │   ├── ./thirdparty/rhs/drivers/CMakeLists.txt
│   │   │   └── ./thirdparty/rhs/drivers/eeprom
│   │   │       ├── ./thirdparty/rhs/drivers/eeprom/CMakeLists.txt
│   │   │       ├── ./thirdparty/rhs/drivers/eeprom/eeprom.c
│   │   │       └── ./thirdparty/rhs/drivers/eeprom/eeprom.h
│   │   ├── ./thirdparty/rhs/hal
│   │   │   ├── ./thirdparty/rhs/hal/CMakeLists.txt
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal.c
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_can
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_can/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_can/rhs_hal_can.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_can/rhs_hal_can.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_cortex
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_cortex/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_cortex/rhs_hal_cortex.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_cortex/rhs_hal_cortex.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_eth
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_eth/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_eth/rhs_hal_eth.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_eth/rhs_hal_eth.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_flash_ex
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_flash_ex/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_flash_ex/mt25ql128aba
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_flash_ex/mt25ql128aba/CMakeLists.txt
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_flash_ex/mt25ql128aba/mt25ql128aba.c
│   │   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_flash_ex/mt25ql128aba/mt25ql128aba.h
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_flash_ex/rhs_hal_flash_ex.c
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_flash_ex/rhs_hal_flash_ex.h
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_flash_ex/usage_example.md
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_gpio
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_gpio/CMakeLists.txt
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_gpio/rhs_hal_gpio.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_i2c
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_i2c/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_i2c/rhs_hal_i2c.c
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_i2c/rhs_hal_i2c.h
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_i2c/rhs_hal_i2c_config.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_i2c/rhs_hal_i2c_type.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_interrupt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_interrupt/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_interrupt/rhs_hal_interrupt.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_interrupt/rhs_hal_interrupt.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_io
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_io/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_io/rhs_hal_io.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_io/rhs_hal_io.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_power
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_power/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_power/rhs_hal_power.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_power/rhs_hal_power.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_random
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_random/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_random/rhs_hal_random.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_random/rhs_hal_random.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_rtc
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_rtc/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_rtc/rhs_hal_rtc.c
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_rtc/rhs_hal_rtc.h
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_rtc/unixtime
│   │   │   │       ├── ./thirdparty/rhs/hal/rhs_hal_rtc/unixtime/CMakeLists.txt
│   │   │   │       ├── ./thirdparty/rhs/hal/rhs_hal_rtc/unixtime/unixtime.c
│   │   │   │       └── ./thirdparty/rhs/hal/rhs_hal_rtc/unixtime/unixtime.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/internal
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/internal/hal_rs232.c
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/internal/hal_rs232.h
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/internal/hal_rs422.c
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/internal/hal_rs422.h
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/internal/hal_rs485.c
│   │   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/internal/hal_rs485.h
│   │   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_serial/internal/rhs_hal_serial_types_i.h
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_serial/rhs_hal_serial.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_serial/rhs_hal_serial.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_speaker
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_speaker/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_speaker/rhs_hal_speaker.c
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_speaker/rhs_hal_speaker.h
│   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb/CMakeLists.txt
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb/rhs_hal_usb.c
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb/rhs_hal_usb.h
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb/rhs_hal_usb_cdc.c
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb/rhs_hal_usb_cdc.h
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb/tud_net_dispatch.c
│   │   │   │   ├── ./thirdparty/rhs/hal/rhs_hal_usb/tud_net_dispatch.h
│   │   │   │   └── ./thirdparty/rhs/hal/rhs_hal_usb/usb_descriptors.c
│   │   │   └── ./thirdparty/rhs/hal/rhs_hal_version
│   │   │       ├── ./thirdparty/rhs/hal/rhs_hal_version/CMakeLists.txt
│   │   │       ├── ./thirdparty/rhs/hal/rhs_hal_version/rhs_hal_version.c
│   │   │       └── ./thirdparty/rhs/hal/rhs_hal_version/rhs_hal_version.h
│   │   ├── ./thirdparty/rhs/rhs.c
│   │   └── ./thirdparty/rhs/rhs.h
│   ├── ./thirdparty/rserial
│   │   ├── ./thirdparty/rserial/CMakeLists.txt
│   │   ├── ./thirdparty/rserial/README.md
│   │   ├── ./thirdparty/rserial/rserial.c
│   │   ├── ./thirdparty/rserial/rserial.h
│   │   ├── ./thirdparty/rserial/rserial_def.h
│   │   ├── ./thirdparty/rserial/test
│   │   │   ├── ./thirdparty/rserial/test/socatfortests.sh
│   │   │   └── ./thirdparty/rserial/test/test.c
│   │   └── ./thirdparty/rserial/utils
│   │       ├── ./thirdparty/rserial/utils/rserial_term.c
│   │       ├── ./thirdparty/rserial/utils/screen.c
│   │       ├── ./thirdparty/rserial/utils/screen.h
│   │       ├── ./thirdparty/rserial/utils/tty.c
│   │       └── ./thirdparty/rserial/utils/tty.h
│   ├── ./thirdparty/rtimer
│   │   ├── ./thirdparty/rtimer/CMakeLists.txt
│   │   ├── ./thirdparty/rtimer/README.md
│   │   ├── ./thirdparty/rtimer/rtimer.c
│   │   ├── ./thirdparty/rtimer/rtimer.h
│   │   ├── ./thirdparty/rtimer/rtimer_def.h
│   │   └── ./thirdparty/rtimer/test
│   │       └── ./thirdparty/rtimer/test/test.c
│   ├── ./thirdparty/runit
│   │   ├── ./thirdparty/runit/CMakeLists.txt
│   │   ├── ./thirdparty/runit/README.md
│   │   ├── ./thirdparty/runit/compiler_flags.cmake
│   │   ├── ./thirdparty/runit/examples
│   │   │   └── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/CMakeLists.txt
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/JLinkRTTViewer.png
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/Ozone.png
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/README.md
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/STM32F103.svd
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/STM32F103RETX_FLASH.ld
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/main.c
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/startup_stm32f103xe.s
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/stm32f103xe.h
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/syscalls.c
│   │   │       ├── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/sysinit.c
│   │   │       └── ./thirdparty/runit/examples/f103re-cmake-baremetal-builtin/system_stm32f1xx.h
│   │   ├── ./thirdparty/runit/src
│   │   │   ├── ./thirdparty/runit/src/runit.c
│   │   │   └── ./thirdparty/runit/src/runit.h
│   │   └── ./thirdparty/runit/tst
│   │       └── ./thirdparty/runit/tst/selftest.c
├── ./toolchains
│   ├── ./toolchains/g0b1.cmake
│   ├── ./toolchains/plc_l.cmake
│   ├── ./toolchains/plc_m.cmake
│   └── ./toolchains/plc_xl.cmake
├── ./user_apps
│   ├── ./user_apps/CMakeLists.txt
│   ├── ./user_apps/cdc_net_hello_rhs
│   │   ├── ./user_apps/cdc_net_hello_rhs/CMakeLists.txt
│   │   ├── ./user_apps/cdc_net_hello_rhs/cdc_net_hello_rhs.c
│   │   └── ./user_apps/cdc_net_hello_rhs/dist
│   │       └── ./user_apps/cdc_net_hello_rhs/dist/index.html
│   └── ./user_apps/eth_net_hello_rhs
│       ├── ./user_apps/eth_net_hello_rhs/CMakeLists.txt
│       ├── ./user_apps/eth_net_hello_rhs/dist
│       │   └── ./user_apps/eth_net_hello_rhs/dist/index.html
│       └── ./user_apps/eth_net_hello_rhs/eth_net_hello_rhs.c
├── ./user_tests
│   ├── ./user_tests/CMakeLists.txt
│   └── ./user_tests/eeprom_test
│       ├── ./user_tests/eeprom_test/CMakeLists.txt
│       └── ./user_tests/eeprom_test/eeprom_test.c
└── ./uv.lock

```