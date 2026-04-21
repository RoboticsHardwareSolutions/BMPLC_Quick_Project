# core directory

This directory contains low-level project configuration and MCU-family specific startup/HAL integration files.

## File map

### core/inc

#### Common headers
- `core/inc/FreeRTOSConfig.h` - FreeRTOS kernel configuration for task scheduling, memory, hooks, and optional features.
- `core/inc/co_config_custom.h` - Custom CANopen stack compile-time configuration.
- `core/inc/lwipopts.h` - lwIP stack configuration (buffers, protocols, memory, and feature switches).
- `core/inc/mongoose_config.h` - Mongoose networking library build-time options.
- `core/inc/stm32.h` - Common STM32 include/selection layer used by project sources.

#### STM32F1-specific headers
- `core/inc/f1/stm32f1xx_hal_conf.h` - HAL module enable/config header for STM32F1 builds.
- `core/inc/f1/tusb_config.h` - TinyUSB compile-time configuration for STM32F1 target. (Because of the unique USB peripheral on F1).
- `core/inc/f1/netif/ethernet.h` - Ethernet network interface declarations used by networking integration. (This is used by tinyUSB CDC-ECM/RNDIS and lwIP Ethernet interfaces. It is here because only BMPLC_M has USB now!!!).

#### STM32F7-specific headers
- `core/inc/f7/stm32f7xx_hal_conf.h` - HAL module enable/config header for STM32F7 builds.

#### STM32G0-specific headers
- `core/inc/g0/stm32g0xx_hal_conf.h` - HAL module enable/config header for STM32G0 builds.

### core/src

#### Common runtime support
- `core/src/syscalls.c` - Newlib/syscall stubs and runtime hooks required by libc in bare-metal/RTOS environment.
- `core/src/sysmem.c` - Heap boundary and memory allocation support hooks for embedded runtime.

#### STM32F1-specific sources
- `core/src/f1/stm32f1xx_hal_msp.c` - HAL MSP (MCU Support Package) initialization/deinitialization for low-level peripherals.
- `core/src/f1/stm32f1xx_hal_timebase_tim.c` - HAL time base implementation using a hardware timer instead of SysTick.
- `core/src/f1/system_stm32f1xx.c` - System startup/clock setup and CMSIS system functions for STM32F1.

#### STM32F7-specific sources
- `core/src/f7/stm32f7xx_hal_timebase_tim.c` - HAL time base implementation using a hardware timer for STM32F7.
- `core/src/f7/system_stm32f7xx.c` - System startup/clock setup and CMSIS system functions for STM32F7.

#### STM32G0-specific sources
- `core/src/g0/stm32g0xx_hal_msp.c` - HAL MSP initialization/deinitialization for STM32G0 peripherals.
- `core/src/g0/system_stm32g0xx.c` - System startup/clock setup and CMSIS system functions for STM32G0.

## Notes
- Only one MCU-family set is effectively used in a given firmware build, selected by the project target (`BMPLC_M`, `BMPLC_L`, `BMPLC_XL`) in root CMake configuration.
- Update files in this directory when changing platform-level behavior: clocks, HAL modules, middleware compile-time options, or libc runtime stubs.
