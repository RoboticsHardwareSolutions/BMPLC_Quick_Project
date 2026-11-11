cmake_minimum_required(VERSION 3.24)
project(usb_bridge_test C)
set(CMAKE_C_STANDARD 11)

if(NOT RHS_SERVICE_USB_BRIDGE)
    message(FATAL_ERROR "RHS_TEST_USB_BRIDGE / RHS_TEST_USB_BRIDGE_APP need RHS_SERVICE_USB_BRIDGE ON")
endif()

add_library(${PROJECT_NAME} STATIC)

target_link_libraries(${PROJECT_NAME}
        PRIVATE
        rhs
        rhs_hal
        runit
        cli
        usb_bridge
)

# slcan.c unit tests, CLI command slcan_test
if(RHS_TEST_USB_BRIDGE)
    target_sources(${PROJECT_NAME} PRIVATE target/slcan_test.c)
    test(rhs_slcan_test)
endif()

# App mode echo application, CLI command usb_bridge_echo, host tests in testbench/
if(RHS_TEST_USB_BRIDGE_APP)
    target_sources(${PROJECT_NAME} PRIVATE target/usb_bridge_echo.c)
    start_up(usb_bridge_echo_start_up)
endif()
