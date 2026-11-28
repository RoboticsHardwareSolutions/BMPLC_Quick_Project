cmake_minimum_required(VERSION 3.24)
project(can_hal_test C)
set(CMAKE_C_STANDARD 11)

if(NOT TARGET rhs_hal_can)
    message(FATAL_ERROR "RHS_TEST_CAN needs rhs_hal_can built: turn on RHS_HAL_CAN, RHS_SERVICE_CAN_OPEN or RHS_SERVICE_USB_BRIDGE")
endif()

add_library(${PROJECT_NAME} STATIC target/can_hal_test.c)

target_include_directories(
        ${PROJECT_NAME} PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
)

target_link_libraries(
        ${PROJECT_NAME}
        PRIVATE
        rhs
        rhs_hal
        cli
)

test(rhs_can_hal_test)
