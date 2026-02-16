set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_VERSION 1)
cmake_minimum_required(VERSION 3.24)

set(PLC_TYPE "BMPLC_M" CACHE STRING "Choose BMPLC_TYPE (BMPLC_M or BMPLC_L or BMPLC_XL)")

if(PLC_TYPE MATCHES "BMPLC_XL")
    set(CMAKE_TOOLCHAIN_FILE ${CMAKE_SOURCE_DIR}/toolchains/plc_xl.cmake CACHE STRING "Toolchain file")
elseif(PLC_TYPE MATCHES "BMPLC_L")
    set(CMAKE_TOOLCHAIN_FILE ${CMAKE_SOURCE_DIR}/toolchains/plc_l.cmake CACHE STRING "Toolchain file")
elseif(PLC_TYPE MATCHES "BMPLC_M")
    set(CMAKE_TOOLCHAIN_FILE ${CMAKE_SOURCE_DIR}/toolchains/plc_m.cmake CACHE STRING "Toolchain file")
else()
    message(FATAL_ERROR "Invalid PLC_TYPE: ${PLC_TYPE}. Please choose BMPLC_M, BMPLC_L, or BMPLC_XL. Or create a custom toolchain file and set CMAKE_TOOLCHAIN_FILE to point to it.")
endif()

# project settings
project(bmplc C CXX ASM)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_C_STANDARD 11)


# RHS Core settings
include(thirdparty/rhs/cmake/rhs.cmake)

add_executable(${PROJECT_NAME} main.c ${SOURCES} ${LINKER_SCRIPT})

# add packed_fs.c explicitly, as it is generated and may not be present at configuration time
target_link_libraries(${CMAKE_PROJECT_NAME} PUBLIC rhs rhs_hal)

set_target_properties(${PROJECT_NAME} PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")


set(HEX_FILE ${PROJECT_BINARY_DIR}/${PROJECT_NAME}.hex)
set(BIN_FILE ${PROJECT_BINARY_DIR}/${PROJECT_NAME}.bin)

add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -Oihex $<TARGET_FILE:${PROJECT_NAME}> ${HEX_FILE}
    COMMAND ${CMAKE_OBJCOPY} -Obinary $<TARGET_FILE:${PROJECT_NAME}> ${BIN_FILE}
    COMMENT "Building ${HEX_FILE}
Building ${BIN_FILE}")

add_subdirectory(thirdparty)
add_subdirectory(rlibs)
add_subdirectory(user_tests)

rhs_report()

# Extract only the directory name from the build path
get_filename_component(CMAKE_BINARY_DIR_NAME "${CMAKE_BINARY_DIR}" NAME)
configure_file(
    "${CMAKE_SOURCE_DIR}/.vscode/example/settings.json.in"
    "${CMAKE_SOURCE_DIR}/.vscode/settings.json"
    @ONLY
)
