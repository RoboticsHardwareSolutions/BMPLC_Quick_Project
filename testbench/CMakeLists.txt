cmake_minimum_required(VERSION 3.24)
project(testbench_daemon C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Debug)
endif()

# Standalone host-native build. Never add_subdirectory()'d from the repo-root
# CMakeLists.txt, which forces an ARM cross-toolchain before project().
set(TB_THIRDPARTY_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../thirdparty")

find_package(Threads REQUIRED)

# ---- tomlc17: single translation unit, no build system of its own ----
add_library(tomlc17 STATIC ${TB_THIRDPARTY_DIR}/tomlc17/src/tomlc17.c)
target_include_directories(tomlc17 PUBLIC ${TB_THIRDPARTY_DIR}/tomlc17/src)

# ---- libmodbus: autotools-generated config.h, then compile sources directly ----
set(LIBMODBUS_SOURCE_DIR "${TB_THIRDPARTY_DIR}/libmodbus")

if(NOT EXISTS "${LIBMODBUS_SOURCE_DIR}/config.h")
    # Stale/broken symlinks in m4/ (seen on macOS, where they can point at
    # /usr/share/aclocal/) break autoreconf -- remove them unconditionally first.
    file(REMOVE
        "${LIBMODBUS_SOURCE_DIR}/m4/libtool.m4"
        "${LIBMODBUS_SOURCE_DIR}/m4/ltoptions.m4"
        "${LIBMODBUS_SOURCE_DIR}/m4/ltsugar.m4"
        "${LIBMODBUS_SOURCE_DIR}/m4/ltversion.m4"
        "${LIBMODBUS_SOURCE_DIR}/m4/lt~obsolete.m4"
    )

    message(STATUS "libmodbus: config.h missing, running autogen.sh")
    execute_process(
        COMMAND sh ./autogen.sh
        WORKING_DIRECTORY "${LIBMODBUS_SOURCE_DIR}"
        RESULT_VARIABLE AUTOGEN_RESULT
        OUTPUT_VARIABLE AUTOGEN_OUT
        ERROR_VARIABLE AUTOGEN_ERR
    )
    if(NOT AUTOGEN_RESULT EQUAL 0)
        message(FATAL_ERROR "libmodbus: autogen.sh failed:\n${AUTOGEN_ERR}")
    endif()

    message(STATUS "libmodbus: running configure")
    execute_process(
        COMMAND sh ./configure
        WORKING_DIRECTORY "${LIBMODBUS_SOURCE_DIR}"
        RESULT_VARIABLE CONFIGURE_RESULT
        OUTPUT_VARIABLE CONFIGURE_OUT
        ERROR_VARIABLE CONFIGURE_ERR
    )
    if(NOT CONFIGURE_RESULT EQUAL 0)
        message(FATAL_ERROR "libmodbus: configure failed:\n${CONFIGURE_ERR}")
    endif()
    message(STATUS "libmodbus: config.h generated")
else()
    message(STATUS "libmodbus: config.h already present, skipping autogen/configure")
endif()

# modbus-tcp.c is intentionally excluded: this daemon only ever uses the RTU backend,
# and modbus-tcp.c fails to build on macOS (IPTOS_LOWDELAY isn't declared by the
# system headers there). Nothing in modbus.c/modbus-rtu.c references its symbols.
add_library(modbus STATIC
    ${LIBMODBUS_SOURCE_DIR}/src/modbus.c
    ${LIBMODBUS_SOURCE_DIR}/src/modbus-data.c
    ${LIBMODBUS_SOURCE_DIR}/src/modbus-rtu.c
)
target_include_directories(modbus PUBLIC
    ${LIBMODBUS_SOURCE_DIR}/src
    ${LIBMODBUS_SOURCE_DIR}
)

# ---- mongoose: reuse the vendored sources, built a second time, host-native
# (the thirdparty/CMakeLists.txt `mongoose` target is cross-compiled for ARM and
# can't be reused here). Not linked into any target yet -- wired up in the HTTP stage. ----
add_library(mongoose_host STATIC ${TB_THIRDPARTY_DIR}/mongoose/mongoose.c)
target_include_directories(mongoose_host PUBLIC ${TB_THIRDPARTY_DIR}/mongoose)

# ---- nng: own CMake build, used by the IPC stage ----
set(NNG_TESTS OFF CACHE BOOL "" FORCE)
set(NNG_TOOLS OFF CACHE BOOL "" FORCE)
set(NNG_ENABLE_NNGCAT OFF CACHE BOOL "" FORCE)
add_subdirectory(${TB_THIRDPARTY_DIR}/nng ${CMAKE_BINARY_DIR}/nng)

# Low-latency C client for the daemon's NNG IPC API -- used by main.c itself (to route
# one-shot CLI commands through an already-running daemon) and reusable standalone by
# anything else that wants to talk to the daemon without touching the serial port.
add_library(testbench_client STATIC client/c/testbench_client.c)
target_include_directories(testbench_client PUBLIC client/c include)
target_link_libraries(testbench_client PUBLIC nng)

add_executable(testbench
    src/main.c
    src/config.c
    src/state.c
    src/modbus_io.c
    src/cli.c
    src/iface_scan.c
    src/http_server.c
    src/ipc_server.c
    src/daemonize.c
    src/usb_resolve.c
)
target_include_directories(testbench PRIVATE include)
target_link_libraries(testbench PRIVATE tomlc17 modbus mongoose_host nng testbench_client Threads::Threads)
if(APPLE)
    target_link_libraries(testbench PRIVATE "-framework IOKit" "-framework CoreFoundation")
endif()

# ---- example programs (see examples/README.md) ----
# 01: the bare C API, no label resolution -- just testbench_client.h.
add_executable(example_read_inputs examples/c/01_read_inputs.c)
target_link_libraries(example_read_inputs PRIVATE testbench_client)

# 02: realistic usage -- also parses testbench.toml (via the daemon's own config.c)
# to resolve a label name to a bit position, the way testbench_client.py's
# TestbenchLabels does on the Python side.
add_executable(example_toggle_output examples/c/02_toggle_output.c src/config.c)
target_include_directories(example_toggle_output PRIVATE src)
target_link_libraries(example_toggle_output PRIVATE testbench_client tomlc17)
