#include "state.h"

#include <string.h>
#include <sys/time.h>

void tb_state_init(TbState* st, int output_span)
{
    memset(st, 0, sizeof(*st));
    pthread_mutex_init(&st->mutex, NULL);
    st->output_span  = output_span;
    st->start_ts_ms = tb_now_ms();
}

void tb_state_destroy(TbState* st)
{
    pthread_mutex_destroy(&st->mutex);
}

uint64_t tb_now_ms(void)
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (uint64_t) tv.tv_sec * 1000ULL + (uint64_t) (tv.tv_usec / 1000);
}
