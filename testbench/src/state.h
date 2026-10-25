#pragma once

#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>

#include "config.h"

typedef struct
{
    pthread_mutex_t mutex;

    uint32_t input_bits;
    uint64_t input_ts_ms;
    bool     input_valid;

    uint8_t  output_bits[TB_MAX_OUTPUT_SPAN]; /* one byte per coil (0/1), index = addr - output_min_addr */
    int      output_span;
    uint64_t output_ts_ms;

    uint64_t poll_count;
    uint64_t poll_errors;
    uint64_t start_ts_ms;
} TbState;

void     tb_state_init(TbState* st, int output_span);
void     tb_state_destroy(TbState* st);
uint64_t tb_now_ms(void);
