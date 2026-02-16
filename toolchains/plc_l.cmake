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

add_compile_definitions(ARM_MATH_CM7;ARM_MATH_MATRIX_CHECK;ARM_MATH_ROUNDING)
add_compile_options(-mfloat-abi=hard -mfpu=fpv4-sp-d16)
add_link_options(-mfloat-abi=hard -mfpu=fpv4-sp-d16)
add_link_options(-Wl,-gc-sections,--print-memory-usage)
add_link_options(-mcpu=cortex-m7 -mthumb -mthumb-interwork)

#Uncomment for software floating point
#add_compile_options(-mfloat-abi=soft)

add_compile_options(-mcpu=cortex-m7 -mthumb -mthumb-interwork)
add_compile_options(-ffunction-sections -fdata-sections -fno-common -fmessage-length=0)

# uncomment to mitigate c++17 absolute addresses warnings
#set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-register")

include_directories(
    core/inc
    core/inc/f7
    thirdparty/stm32f7_hal/Inc
    thirdparty/stm32f7_hal/Inc/Legacy
    thirdparty/stm32f7_cmsis/Include
    thirdparty/cmsis/CMSIS/Core/Include
)

add_definitions(-DUSE_HAL_DRIVER -DSTM32F765xx)

file(GLOB_RECURSE SOURCES "core/src/syscalls.c" "core/src/sysmem.c" "core/src/f7/*.*" "thirdparty/stm32f7_hal/*.*" "thirdparty/stm32f7_cmsis/Source/Templates/gcc/startup_stm32f765xx.s")
list(FILTER SOURCES EXCLUDE REGEX "_template[.]c$")

set(LINKER_SCRIPT ${CMAKE_SOURCE_DIR}/STM32F765ZGTX_FLASH.ld)

add_link_options(-Wl,-gc-sections,--print-memory-usage,-Map=${PROJECT_BINARY_DIR}/${PROJECT_NAME}.map)
add_link_options(-T ${LINKER_SCRIPT})

################################################## RHS configuration ##################################################
add_definitions(-DBMPLC_L)

## set HAL
set(RHS_HAL_FLASH_EX ON)
set(RHS_HAL_IO ON)
set(RHS_HAL_RTC ON)
set(RHS_HAL_SERIAL ON)
set(RHS_HAL_SPEAKER ON)
set(RHS_HAL_CAN ON)
set(RHS_HAL_RANDOM ON)

## set SERVICES
set(RHS_SERVICE_NOTIFICATION ON)
set(RHS_CAN_OPEN ON)

## set TESTS
set(RHS_TEST_MEMMNG ON)
set(RHS_TESTFLASH_EX ON)
set(RHS_TEST_LOG_SAVE ON)
set(RHS_TEST_RECORDS ON)

## set LAUNCHER
set(DEVICE_TYPE "STM32F765ZG")
set(DEVICE_SVD_FILE "STM32F765.svd")
