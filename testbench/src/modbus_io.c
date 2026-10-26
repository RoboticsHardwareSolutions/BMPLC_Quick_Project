#include "modbus_io.h"

#include <errno.h>
#include <modbus.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "usb_resolve.h"

struct TbModbus
{
    modbus_t* ctx;
};

/* Resolves cfg->usb_location to whatever /dev path the adapter is currently
 * enumerated under (that name is not stable across reboots for cheap USB-serial
 * clones, see usb_resolve.h). */
static int resolve_port(const TbConfig* cfg, char* out_port, size_t out_len, char* errbuf, size_t errbuf_len)
{
    if (cfg->usb_location == 0)
    {
        snprintf(errbuf, errbuf_len, "io.connection.usb_location is not set");
        return -1;
    }

    if (tb_usb_resolve(cfg->usb_location, out_port, out_len) != 0)
    {
        snprintf(errbuf, errbuf_len, "no usb device currently at location 0x%x", cfg->usb_location);
        return -1;
    }

    return 0;
}

/* Creates and connects a fresh libmodbus RTU context for cfg's port. Used both for the
 * initial open and for reconnecting after the serial device drops out (e.g. a USB-serial
 * adapter unplugged/replugged, which leaves the old fd pointing at a removed device node),
 * and -- via the public tb_modbus_open_ctx() below -- for one-shot CLI sessions. */
modbus_t* tb_modbus_open_ctx(const TbConfig* cfg, char* errbuf, size_t errbuf_len)
{
    char port[256];
    if (resolve_port(cfg, port, sizeof(port), errbuf, errbuf_len) != 0)
        return NULL;

    modbus_t* ctx = modbus_new_rtu(port, cfg->baudrate, 'N', 8, 1);
    if (!ctx)
    {
        snprintf(errbuf, errbuf_len, "modbus_new_rtu(%s): %s", port, modbus_strerror(errno));
        return NULL;
    }

    uint32_t to_sec  = (uint32_t) cfg->timeout_s;
    uint32_t to_usec = (uint32_t) ((cfg->timeout_s - (double) to_sec) * 1000000.0);
    modbus_set_response_timeout(ctx, to_sec, to_usec);

    if (modbus_connect(ctx) != 0)
    {
        snprintf(errbuf, errbuf_len, "modbus_connect(%s): %s", port, modbus_strerror(errno));
        modbus_free(ctx);
        return NULL;
    }

    return ctx;
}

int tb_modbus_read_registers_retry(modbus_t* ctx, int addr, int n, uint16_t* dest, int attempts)
{
    if (attempts < 1)
        attempts = 1;
    int rc = -1;
    for (int a = 0; a < attempts; a++)
    {
        rc = modbus_read_registers(ctx, addr, n, dest);
        if (rc == n)
            return rc;
        if (a + 1 < attempts)
            usleep(50000);
    }
    return rc;
}

int tb_modbus_read_bits_retry(modbus_t* ctx, int addr, int n, uint8_t* dest, int attempts)
{
    if (attempts < 1)
        attempts = 1;
    int rc = -1;
    for (int a = 0; a < attempts; a++)
    {
        rc = modbus_read_bits(ctx, addr, n, dest);
        if (rc == n)
            return rc;
        if (a + 1 < attempts)
            usleep(50000);
    }
    return rc;
}

int tb_modbus_write_bits_retry(modbus_t* ctx, int addr, int n, const uint8_t* data, int attempts)
{
    if (attempts < 1)
        attempts = 1;
    int rc = -1;
    for (int a = 0; a < attempts; a++)
    {
        rc = modbus_write_bits(ctx, addr, n, data);
        if (rc == n)
            return rc;
        if (a + 1 < attempts)
            usleep(50000);
    }
    return rc;
}

TbModbus* tb_modbus_open(const TbConfig* cfg, char* errbuf, size_t errbuf_len)
{
    TbModbus* m = calloc(1, sizeof(*m));
    if (!m)
    {
        snprintf(errbuf, errbuf_len, "out of memory");
        return NULL;
    }

    m->ctx = tb_modbus_open_ctx(cfg, errbuf, errbuf_len);
    if (!m->ctx)
    {
        free(m);
        return NULL;
    }

    return m;
}

int tb_modbus_reconnect(TbModbus* m, const TbConfig* cfg, char* errbuf, size_t errbuf_len)
{
    if (m->ctx)
    {
        modbus_close(m->ctx);
        modbus_free(m->ctx);
        m->ctx = NULL;
    }

    m->ctx = tb_modbus_open_ctx(cfg, errbuf, errbuf_len);
    return m->ctx ? 0 : -1;
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

    uint8_t bits[TB_MAX_OUTPUT_SPAN] = {0};
    modbus_set_slave(m->ctx, cfg->outputs_id);
    int rc = tb_modbus_read_bits_retry(m->ctx, cfg->output_min_addr, cfg->output_span, bits, cfg->retries);

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
        st->input_bits  = tb_regs_to_input_bits(regs, n);
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
            st->output_ts_ms  = tb_now_ms();
            st->output_valid = true;
        }
        else
        {
            st->output_valid = false;
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
