#include "modbus_io.h"

#include <errno.h>
#include <modbus.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct TbModbus
{
    modbus_t* ctx;
};

TbModbus* tb_modbus_open(const TbConfig* cfg, char* errbuf, size_t errbuf_len)
{
    TbModbus* m = calloc(1, sizeof(*m));
    if (!m)
    {
        snprintf(errbuf, errbuf_len, "out of memory");
        return NULL;
    }

    m->ctx = modbus_new_rtu(cfg->port, cfg->baudrate, 'N', 8, 1);
    if (!m->ctx)
    {
        snprintf(errbuf, errbuf_len, "modbus_new_rtu(%s): %s", cfg->port, modbus_strerror(errno));
        free(m);
        return NULL;
    }

    uint32_t to_sec  = (uint32_t) cfg->timeout_s;
    uint32_t to_usec = (uint32_t) ((cfg->timeout_s - (double) to_sec) * 1000000.0);
    modbus_set_response_timeout(m->ctx, to_sec, to_usec);

    if (modbus_connect(m->ctx) != 0)
    {
        snprintf(errbuf, errbuf_len, "modbus_connect(%s): %s", cfg->port, modbus_strerror(errno));
        modbus_free(m->ctx);
        free(m);
        return NULL;
    }

    return m;
}

void tb_modbus_close(TbModbus* m)
{
    if (!m)
        return;
    if (m->ctx)
    {
        modbus_close(m->ctx);
        modbus_free(m->ctx);
    }
    free(m);
}

int tb_modbus_seed_outputs(TbModbus* m, const TbConfig* cfg, TbState* st)
{
    if (cfg->output_span <= 0)
        return 0;

    /* One-shot, like the CLI transactions -- there's no next poll cycle to fall back on
     * if this single read hits transient RS485 bus noise, so retry a few times. */
    uint8_t bits[TB_MAX_OUTPUT_SPAN] = {0};
    modbus_set_slave(m->ctx, cfg->outputs_id);
    int attempts = cfg->retries < 1 ? 1 : cfg->retries;
    int rc       = -1;
    for (int a = 0; a < attempts; a++)
    {
        rc = modbus_read_bits(m->ctx, cfg->output_min_addr, cfg->output_span, bits);
        if (rc == cfg->output_span)
            break;
        if (a + 1 < attempts)
            usleep(50000);
    }

    pthread_mutex_lock(&st->mutex);
    if (rc == cfg->output_span)
        memcpy(st->output_bits, bits, (size_t) cfg->output_span);
    st->output_span = cfg->output_span;
    pthread_mutex_unlock(&st->mutex);

    return rc == cfg->output_span ? 0 : -1;
}

int tb_modbus_cycle(TbModbus* m, const TbConfig* cfg, TbState* st)
{
    int ok = 0;

    /* 1. read inputs (holding registers) */
    uint16_t regs[TB_MAX_INPUT_REGS] = {0};
    int      n                       = cfg->input_count;
    modbus_set_slave(m->ctx, cfg->inputs_id);
    int rc = modbus_read_registers(m->ctx, cfg->input_start_address, n, regs);

    pthread_mutex_lock(&st->mutex);
    if (rc == n)
    {
        uint32_t bits = 0;
        for (int i = 0; i < n; i++)
            bits |= ((uint32_t) regs[i]) << (16 * i);
        st->input_bits  = bits;
        st->input_valid = true;
        st->input_ts_ms = tb_now_ms();
    }
    else
    {
        st->input_valid = false;
        st->poll_errors++;
        ok = -1;
    }
    pthread_mutex_unlock(&st->mutex);

    /* 2. always rewrite the whole output coil span from the in-memory desired state --
     * this is what defeats the modules' bus-error watchdog even when nothing changed. */
    if (cfg->output_span > 0)
    {
        uint8_t bits[TB_MAX_OUTPUT_SPAN];
        pthread_mutex_lock(&st->mutex);
        memcpy(bits, st->output_bits, (size_t) cfg->output_span);
        pthread_mutex_unlock(&st->mutex);

        modbus_set_slave(m->ctx, cfg->outputs_id);
        int wrc = modbus_write_bits(m->ctx, cfg->output_min_addr, cfg->output_span, bits);

        pthread_mutex_lock(&st->mutex);
        if (wrc == cfg->output_span)
        {
            st->output_ts_ms = tb_now_ms();
        }
        else
        {
            st->poll_errors++;
            ok = -1;
        }
        pthread_mutex_unlock(&st->mutex);
    }

    pthread_mutex_lock(&st->mutex);
    st->poll_count++;
    pthread_mutex_unlock(&st->mutex);

    return ok;
}
