# Common part of the board toolchains: arm-none-eabi compiler, build types, MCU flags, sources and linker script.
# Not a toolchain on its own: a board file sets the variables below and then includes this file.
#
#   MCU_CPU        -mcpu value: cortex-m0plus / cortex-m3 / cortex-m7
#   MCU_FPU_FLAGS  float ABI flags for compiler and linker, empty for soft float
#   MCU_FAMILY     STM32 family suffix: core/inc/<family>, core/src/<family>, thirdparty/stm32<family>_hal, ..._cmsis
#   MCU_STARTUP    startup file in thirdparty/stm32<family>_cmsis/Source/Templates/gcc
#   MCU_DEFINES    MCU, HAL and board compile definitions
#   LINKER_SCRIPT  path to the .ld file
#
# Provides SOURCES (MCU startup, HAL and core/ files) and LINKER_SCRIPT for add_executable().

foreach(required MCU_CPU MCU_FAMILY MCU_STARTUP MCU_DEFINES LINKER_SCRIPT)
    if(NOT DEFINED ${required})
        message(FATAL_ERROR "${required} must be set before include(common.cmake)")
    endif()
endforeach()

########################################## Compiler ##########################################

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

########################################## Build type ########################################

if("${CMAKE_BUILD_TYPE}" STREQUAL "Release")
    message(STATUS "Maximum optimization for speed")
    add_compile_options(-Ofast)
elseif("${CMAKE_BUILD_TYPE}" STREQUAL "RelWithDebInfo")
    message(STATUS "Maximum optimization for speed, debug info included")
    add_compile_options(-Ofast -g)
elseif("${CMAKE_BUILD_TYPE}" STREQUAL "MinSizeRel")
    message(STATUS "Maximum optimization for size")
    add_compile_options(-g -Os)
elseif("${CMAKE_BUILD_TYPE}" STREQUAL "MinOptDebInfo")
    message(STATUS "Optimization for debugging")
    add_compile_options(-Og -g)
else()
    message(STATUS "No optimization")
    add_compile_options(-g)
endif()

########################################## MCU ###############################################

# -mcpu must stay in the directory compile options: thirdparty/CMakeLists.txt reads it to choose the FreeRTOS port
add_compile_options(${MCU_FPU_FLAGS} -mcpu=${MCU_CPU} -mthumb)
add_compile_options(-ffunction-sections -fdata-sections -fno-common -fmessage-length=0)
add_link_options(${MCU_FPU_FLAGS} -mcpu=${MCU_CPU} -mthumb)

add_compile_definitions(${MCU_DEFINES})

include_directories(
    core/inc
    core/inc/${MCU_FAMILY}
    thirdparty/stm32${MCU_FAMILY}_hal/Inc
    thirdparty/stm32${MCU_FAMILY}_hal/Inc/Legacy
    thirdparty/stm32${MCU_FAMILY}_cmsis/Include
    thirdparty/cmsis/CMSIS/Core/Include
)

file(GLOB_RECURSE SOURCES
    "core/src/syscalls.c"
    "core/src/sysmem.c"
    "core/src/${MCU_FAMILY}/*.*"
    "thirdparty/stm32${MCU_FAMILY}_hal/*.*"
    "thirdparty/stm32${MCU_FAMILY}_cmsis/Source/Templates/gcc/${MCU_STARTUP}"
)
list(FILTER SOURCES EXCLUDE REGEX "_template[.]c$")

########################################## Linker ############################################

add_link_options(-Wl,-gc-sections,--print-memory-usage,-Map=${PROJECT_BINARY_DIR}/${PROJECT_NAME}.map)
add_link_options(-T ${LINKER_SCRIPT})
