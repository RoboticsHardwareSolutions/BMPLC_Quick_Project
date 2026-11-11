# G0B1: STM32G0B1KC, Cortex-M0+
# Selected by PLC_TYPE in the root CMakeLists.txt, common part is in common.cmake

################################################## Board ##################################################

set(MCU_CPU cortex-m0plus)
set(MCU_FPU_FLAGS "")
set(MCU_FAMILY g0)
set(MCU_STARTUP startup_stm32g0b1xx.s)
set(MCU_DEFINES
    USE_HAL_DRIVER
    USE_FULL_LL_DRIVER
    STM32G0B1xx
)
set(LINKER_SCRIPT ${CMAKE_CURRENT_LIST_DIR}/STM32G0B1KCUX_FLASH.ld)

set(DEVICE_TYPE "STM32G0B1KC")
set(DEVICE_SVD_FILE "toolchains/STM32G0B1.svd")

include(${CMAKE_CURRENT_LIST_DIR}/common.cmake)

################################################## RHS configuration ##################################################

## HAL (also enabled by the services that need them)
set(RHS_HAL_SPEAKER OFF)
set(RHS_HAL_FLASH_EX OFF)
set(RHS_HAL_RTC OFF)
set(RHS_HAL_I2C OFF)
set(RHS_HAL_SERIAL OFF)
set(RHS_HAL_CAN OFF)
set(RHS_HAL_RANDOM OFF)
set(RHS_HAL_USB OFF)
set(RHS_HAL_ETH OFF)

## BSP / DRIVERS
set(RHS_DRIVER_EEPROM ON)
set(RHS_BSP_IO OFF)

## SERVICES
set(RHS_SERVICE_NOTIFICATION OFF)
set(RHS_SERVICE_USB_BRIDGE ON)            # USB CDC/NCM bridge to CAN, RS232, RS485, Ethernet

set(RHS_SERVICE_USB_CDC_NET OFF)
set(RHS_USB_CDC_NET_IP "192.168.0.100")
set(RHS_USB_CDC_NET_GATEWAY "192.168.0.1")
set(RHS_USB_CDC_NET_NETMASK "255.255.255.0")

set(RHS_SERVICE_ETH_NET OFF)
set(RHS_ETH_NET_IP "192.168.0.100")
set(RHS_ETH_NET_GATEWAY "192.168.0.1")
set(RHS_ETH_NET_NETMASK "255.255.255.0")

## TESTS
set(RHS_TEST_EEPROM OFF)
set(RHS_TEST_MEMMNG ON)
set(RHS_TEST_RECORDS ON)
set(RHS_TEST_FLASH_EX OFF)
set(RHS_TEST_IO OFF)
set(RHS_TEST_EXTI OFF)
set(RHS_TEST_USB_BRIDGE ON)
set(RHS_TEST_USB_BRIDGE_APP ON)
set(RHS_TEST_USB_MOUNT ON)
