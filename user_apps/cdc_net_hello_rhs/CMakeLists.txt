cmake_minimum_required(VERSION 3.24)
project(cdc_net_hello_rhs C)
set(CMAKE_C_STANDARD 11)

add_library(${PROJECT_NAME} STATIC
    cdc_net_hello_rhs.c
)

target_link_libraries(
    ${PROJECT_NAME}
    PUBLIC
    cdc_net
)

start_up(cdc_net_hello_rhs_start_up)
