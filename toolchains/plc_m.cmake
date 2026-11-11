# BMPLC_M: STM32F103RE, Cortex-M3
# Selected by PLC_TYPE in the root CMakeLists.txt, common part is in common.cmake

################################################## Board ##################################################

set(MCU_CPU cortex-m3)
set(MCU_FPU_FLAGS "")
set(MCU_FAMILY f1)
set(MCU_STARTUP startup_stm32f103xe.s)
set(MCU_DEFINES
    USE_HAL_DRIVER
    USE_FULL_LL_DRIVER
    STM32F103xE
    ARM_MATH_CM3
    ARM_MATH_MATRIX_CHECK
    ARM_MATH_ROUNDING
    BMPLC_M
)
set(LINKER_SCRIPT ${CMAKE_CURRENT_LIST_DIR}/STM32F103RETX_FLASH.ld)

set(DEVICE_TYPE "STM32F103RE")
set(DEVICE_SVD_FILE "toolchains/STM32F103.svd")

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
set(RHS_BSP_IO ON)

## SERVICES
set(RHS_SERVICE_NOTIFICATION ON)
set(RHS_SERVICE_CAN_OPEN ON)
set(RHS_SERVICE_USB_SERIAL_BRIDGE ON)

set(RHS_SERVICE_USB_CDC_NET ON)
set(RHS_USB_CDC_NET_IP "192.168.3.100")
set(RHS_USB_CDC_NET_GATEWAY "192.168.3.1")
set(RHS_USB_CDC_NET_NETMASK "255.255.255.0")

set(RHS_SERVICE_ETH_NET OFF)
set(RHS_ETH_NET_IP "192.168.0.100")
set(RHS_ETH_NET_GATEWAY "192.168.0.1")
set(RHS_ETH_NET_NETMASK "255.255.255.0")

set(RHS_SERVICE_USB_ETH_BRIDGE OFF)

## TESTS
set(RHS_TEST_EEPROM ON)
set(RHS_TEST_MEMMNG ON)
set(RHS_TEST_RECORDS ON)
set(RHS_TEST_FLASH_EX OFF)
set(RHS_TEST_IO ON)
set(RHS_TEST_EXTI ON)
