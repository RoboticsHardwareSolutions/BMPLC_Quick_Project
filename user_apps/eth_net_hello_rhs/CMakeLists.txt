cmake_minimum_required(VERSION 3.24)
project(eth_net_hello_rhs C)
set(CMAKE_C_STANDARD 11)

add_library(${PROJECT_NAME} STATIC
    eth_net_hello_rhs.c
)

target_link_libraries(
    ${PROJECT_NAME}
    PUBLIC
    eth_net
)

start_up(eth_net_hello_rhs_start_up)
