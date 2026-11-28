cmake_minimum_required(VERSION 3.24)
project(adc_test C)
set(CMAKE_C_STANDARD 11)

add_library(${PROJECT_NAME} STATIC adc_test.c)

target_link_libraries(${PROJECT_NAME}
        PRIVATE
        rhs
        rhs_hal
        runit
        cli
)

test(adc_test)
