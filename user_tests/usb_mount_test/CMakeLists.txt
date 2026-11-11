cmake_minimum_required(VERSION 3.24)
project(usb_mount_test C)
set(CMAKE_C_STANDARD 11)

if(NOT TARGET rhs_hal_usb)
    message(FATAL_ERROR "RHS_TEST_USB_MOUNT needs rhs_hal_usb: RHS_HAL_USB or RHS_SERVICE_USB_BRIDGE ON")
endif()

add_library(${PROJECT_NAME} STATIC target/usb_mount_test.c)

target_link_libraries(${PROJECT_NAME}
        PRIVATE
        rhs
        rhs_hal
        runit
        cli
)

# Unit tests of the mount state, CLI command usb_mount_test
test(rhs_usb_mount_test)
# Mount state and event counters for the host tests in testbench/, CLI command usb_mount
start_up(usb_mount_start_up)
