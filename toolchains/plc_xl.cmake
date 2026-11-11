# BMPLC_XL: STM32F765ZG, Cortex-M7
# Selected by PLC_TYPE in the root CMakeLists.txt, common part is in common.cmake

################################################## Board ##################################################

set(MCU_CPU cortex-m7)
set(MCU_FPU_FLAGS -mfloat-abi=hard -mfpu=fpv4-sp-d16)
set(MCU_FAMILY f7)
set(MCU_STARTUP startup_stm32f765xx.s)
set(MCU_DEFINES
    USE_HAL_DRIVER
    STM32F765xx
    ARM_MATH_CM7
    ARM_MATH_MATRIX_CHECK
    ARM_MATH_ROUNDING
    BMPLC_XL
)
set(LINKER_SCRIPT ${CMAKE_CURRENT_LIST_DIR}/STM32F765ZGTX_FLASH.ld)

set(DEVICE_TYPE "STM32F765ZG")
set(DEVICE_SVD_FILE "toolchains/STM32F765.svd")

include(${CMAKE_CURRENT_LIST_DIR}/common.cmake)

################################################## RHS configuration ##################################################

## HAL (also enabled by the services that need them)
set(RHS_HAL_SPEAKER ON)
set(RHS_HAL_FLASH_EX ON)
set(RHS_HAL_RTC ON)
set(RHS_HAL_I2C OFF)
set(RHS_HAL_SERIAL ON)
set(RHS_HAL_CAN ON)
set(RHS_HAL_RANDOM ON)
set(RHS_HAL_USB OFF)
set(RHS_HAL_ETH ON)

## BSP / DRIVERS
set(RHS_DRIVER_EEPROM OFF)
set(RHS_BSP_IO ON)

## SERVICES
set(RHS_SERVICE_NOTIFICATION ON)
set(RHS_SERVICE_CAN_OPEN OFF)
set(RHS_SERVICE_USB_BRIDGE ON)            # USB CDC/NCM bridge to CAN, RS232, RS485, Ethernet

set(RHS_SERVICE_USB_CDC_NET ON)
set(RHS_USB_CDC_NET_IP "192.168.3.100")
set(RHS_USB_CDC_NET_GATEWAY "192.168.3.1")
set(RHS_USB_CDC_NET_NETMASK "255.255.255.0")

set(RHS_SERVICE_ETH_NET ON)
set(RHS_ETH_NET_IP "192.168.2.100")
set(RHS_ETH_NET_GATEWAY "192.168.2.1")
set(RHS_ETH_NET_NETMASK "255.255.255.0")

## TESTS
set(RHS_TEST_EEPROM OFF)
set(RHS_TEST_MEMMNG ON)
set(RHS_TEST_RECORDS ON)
set(RHS_TEST_FLASH_EX ON)
set(RHS_TEST_IO ON)
set(RHS_TEST_EXTI ON)
set(RHS_TEST_USB_BRIDGE ON)
set(RHS_TEST_USB_BRIDGE_APP ON)
set(RHS_TEST_USB_MOUNT ON)
