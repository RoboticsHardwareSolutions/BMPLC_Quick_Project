cmake_minimum_required(VERSION 3.24)
project(flash_ex_test C)
set(CMAKE_C_STANDARD 11)

add_library(${PROJECT_NAME} STATIC flash_ex_unit_test.c)

target_include_directories(
        ${PROJECT_NAME} PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
)

target_link_libraries(${PROJECT_NAME}
        PRIVATE
        rhs
        rhs_hal
        runit
        cli
)

test(flash_ex_test)
