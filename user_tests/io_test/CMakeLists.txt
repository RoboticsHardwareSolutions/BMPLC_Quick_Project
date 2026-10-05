cmake_minimum_required(VERSION 3.24)
project(io_srv C)
set(CMAKE_C_STANDARD 11)

add_library(${PROJECT_NAME} STATIC target/io_test.c)

target_include_directories(
        ${PROJECT_NAME} PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
)

target_link_libraries(
        ${PROJECT_NAME}
        PRIVATE
        notification
        rhs_hal
        cli
)

test(rhs_io_test "rhs_io_test" )
