set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
set(CMAKE_AR arm-none-eabi-ar)
set(CMAKE_OBJCOPY arm-none-eabi-objcopy)
set(CMAKE_OBJDUMP arm-none-eabi-objdump)
set(SIZE arm-none-eabi-size)
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

set(CMAKE_EXECUTABLE_SUFFIX_C .elf)

if("${CMAKE_BUILD_TYPE}" STREQUAL "Release")
    message(STATUS "Maximum optimization for speed")
    add_compile_options(-Ofast)
elseif("${CMAKE_BUILD_TYPE}" STREQUAL "RelWithDebInfo")
    message(STATUS "Maximum optimization for speed, debug info included")
    add_compile_options(-Ofast -g)
elseif("${CMAKE_BUILD_TYPE}" STREQUAL "MinSizeRel")
    add_compile_options(-g)
    message(STATUS "Maximum optimization for size")
    add_compile_options(-Os)
elseif("${CMAKE_BUILD_TYPE}" STREQUAL "MinOptDebInfo")
    message(STATUS "Maximum optimization for size")
    add_compile_options(-Og -g)
else()
    add_compile_options(-g)
    message(STATUS "No optimization")
endif()

add_link_options(-Wl,-gc-sections,--print-memory-usage)

add_compile_options(-mcpu=cortex-m0plus -mthumb -mthumb-interwork)
add_compile_options(-ffunction-sections -fdata-sections -fno-common -fmessage-length=0)
add_link_options(-mcpu=cortex-m0plus -mthumb)

include_directories(
    core/inc
    core/inc/g0
    thirdparty/stm32g0_hal/Inc
    thirdparty/stm32g0_hal/Inc/Legacy
    thirdparty/stm32g0_cmsis/Include
    thirdparty/cmsis/CMSIS/Core/Include
)

add_definitions(-DUSE_HAL_DRIVER -DUSE_FULL_LL_DRIVER -DSTM32G0B1xx)

file(GLOB_RECURSE SOURCES
    "core/src/syscalls.c"
    "core/src/sysmem.c"
    "core/src/g0/*.*"
    "thirdparty/stm32g0_hal/*.*"
    "thirdparty/stm32g0_cmsis/Source/Templates/gcc/startup_stm32g0b1xx.s"
)
list(FILTER SOURCES EXCLUDE REGEX "_template[.]c$")

set(LINKER_SCRIPT ${CMAKE_SOURCE_DIR}/STM32G0B1KCUX_FLASH.ld)

add_link_options(-Wl,-gc-sections,--print-memory-usage,-Map=${PROJECT_BINARY_DIR}/${PROJECT_NAME}.map)
add_link_options(-T ${LINKER_SCRIPT})

################################################## RHS configuration ##################################################

## set HAL
### All necessary HAL libs will be included in the core by services

## set DRIVERS
# set(RHS_DRIVER_EEPROM ON)

## set SERVICES
# set(RHS_SERVICE_NOTIFICATION ON)
# set(RHS_SERVICE_USB_SERIAL_BRIDGE ON)
# set(RHS_SERVICE_CAN_OPEN ON)
# set(RHS_APPLICATION_USB_CDC_NET ON)

## set TESTS
# set(RHS_TEST_MEMMNG ON)
# set(RHS_TEST_LOG_SAVE ON)
# set(RHS_TEST_RECORDS ON)

set(DEVICE_TYPE "STM32G0B1KC")
set(DEVICE_SVD_FILE "STM32G0B1.svd")
