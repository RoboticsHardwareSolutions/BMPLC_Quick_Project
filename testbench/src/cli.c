#include "cli.h"

#include <errno.h>
#include <modbus.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "iface_scan.h"

/* A one-shot CLI call has no next poll cycle to fall back on the way the daemon does,
 * so transient RS485 bus noise (a single corrupted frame, CRC mismatch) would otherwise
 * fail the whole command. Retry up to cfg->retries times, matching the `retries` key
 * already declared (but previously unused) in testbench.toml. */
static int read_registers_retry(modbus_t* ctx, int addr, int n, uint16_t* dest, int attempts)
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

static int read_bits_retry(modbus_t* ctx, int addr, int n, uint8_t* dest, int attempts)
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

static int write_bits_retry(modbus_t* ctx, int addr, int n, const uint8_t* data, int attempts)
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

static modbus_t* open_ctx(const TbConfig* cfg, char* errbuf, size_t errbuf_len)
{
    modbus_t* ctx = modbus_new_rtu(cfg->port, cfg->baudrate, 'N', 8, 1);
    if (!ctx)
    {
        snprintf(errbuf, errbuf_len, "modbus_new_rtu(%s): %s", cfg->port, modbus_strerror(errno));
        return NULL;
    }
    uint32_t to_sec  = (uint32_t) cfg->timeout_s;
    uint32_t to_usec = (uint32_t) ((cfg->timeout_s - (double) to_sec) * 1000000.0);
    modbus_set_response_timeout(ctx, to_sec, to_usec);
    if (modbus_connect(ctx) != 0)
    {
        snprintf(errbuf, errbuf_len, "modbus_connect(%s): %s", cfg->port, modbus_strerror(errno));
        modbus_free(ctx);
        return NULL;
    }
    return ctx;
}

int tb_cli_list(const TbConfig* cfg)
{
    printf("Inputs (holding registers, slave %d, bit index -> label):\n", cfg->inputs_id);
    for (int i = 0; i < cfg->input_label_count; i++)
        printf("  %2d  %s\n", cfg->input_labels[i].index, cfg->input_labels[i].name);

    printf("Outputs (coils, slave %d, address -> label):\n", cfg->outputs_id);
    for (int i = 0; i < cfg->output_label_count; i++)
        printf("  %2d  %s\n", cfg->output_labels[i].index, cfg->output_labels[i].name);

    return 0;
}

int tb_cli_read(const TbConfig* cfg)
{
    char      errbuf[256];
    modbus_t* ctx = open_ctx(cfg, errbuf, sizeof(errbuf));
    if (!ctx)
    {
        fprintf(stderr, "testbench: %s\n", errbuf);
        return 1;
    }

    modbus_set_slave(ctx, cfg->inputs_id);
    uint16_t regs[TB_MAX_INPUT_REGS] = {0};
    int rc = read_registers_retry(ctx, cfg->input_start_address, cfg->input_count, regs, cfg->retries);

    int status = 0;
    if (rc != cfg->input_count)
    {
        fprintf(stderr, "testbench: read failed: %s\n", modbus_strerror(errno));
        status = 1;
    }
    else
    {
        uint32_t bits = 0;
        for (int i = 0; i < cfg->input_count; i++)
            bits |= ((uint32_t) regs[i]) << (16 * i);
        for (int i = 0; i < cfg->input_label_count; i++)
        {
            int idx = cfg->input_labels[i].index;
            printf("  %-20s : %s\n", cfg->input_labels[i].name, ((bits >> idx) & 1u) ? "ON" : "off");
        }
    }

    modbus_close(ctx);
    modbus_free(ctx);
    return status;
}

int tb_parse_write_assignments(const TbConfig* cfg, const char* assignments, uint32_t* out_mask, uint32_t* out_value)
{
    char buf[1024];
    strncpy(buf, assignments, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';

    uint32_t mask = 0, value = 0;
    int      n    = 0;

    char* save = NULL;
    for (char* tok = strtok_r(buf, ",", &save); tok != NULL; tok = strtok_r(NULL, ",", &save))
    {
        char* eq = strchr(tok, '=');
        if (!eq)
        {
            fprintf(stderr, "testbench: bad assignment '%s' (expected LABEL=0|1)\n", tok);
            return 1;
        }
        *eq              = '\0';
        const char* label = tok;
        int         state = atoi(eq + 1) ? 1 : 0;

        int addr = tb_config_find_output_addr(cfg, label);
        if (addr < 0)
        {
            fprintf(stderr, "testbench: unknown output label '%s'\n", label);
            return 1;
        }
        int bit = addr - cfg->output_min_addr;
        if (bit < 0 || bit >= 32)
        {
            /* the (mask, value) wire representation shared with IPC's
             * TB_OP_SET_COILS_MASK is a uint32_t, so it can only address a 32-coil span */
            fprintf(stderr, "testbench: '%s' is outside the 32-coil span this protocol can address\n", label);
            return 1;
        }
        mask |= (1u << bit);
        if (state)
            value |= (1u << bit);
        n++;
    }
    if (n == 0)
    {
        fprintf(stderr, "testbench: no assignments given\n");
        return 1;
    }

    *out_mask  = mask;
    *out_value = value;
    return 0;
}

int tb_cli_write(const TbConfig* cfg, const char* assignments)
{
    uint32_t mask = 0, value = 0;
    if (tb_parse_write_assignments(cfg, assignments, &mask, &value) != 0)
        return 1;

    int lo = -1, hi = -1;
    for (int bit = 0; bit < 32; bit++)
        if (mask & (1u << bit))
        {
            if (lo < 0)
                lo = bit;
            hi = bit;
        }
    int span = hi - lo + 1;
    int base = cfg->output_min_addr + lo;

    char      errbuf[256];
    modbus_t* ctx = open_ctx(cfg, errbuf, sizeof(errbuf));
    if (!ctx)
    {
        fprintf(stderr, "testbench: %s\n", errbuf);
        return 1;
    }
    modbus_set_slave(ctx, cfg->outputs_id);

    /* Read-modify-write over the touched span only, exactly like io.py's write_coils():
     * a one-shot CLI call has no persistent desired-state cache to rewrite from, so it
     * must not blindly zero the coils it wasn't asked to change. */
    uint8_t bits[TB_MAX_OUTPUT_SPAN] = {0};
    if (read_bits_retry(ctx, base, span, bits, cfg->retries) != span)
    {
        fprintf(stderr, "testbench: read-before-write failed: %s\n", modbus_strerror(errno));
        modbus_close(ctx);
        modbus_free(ctx);
        return 1;
    }
    for (int bit = lo; bit <= hi; bit++)
        if (mask & (1u << bit))
            bits[(cfg->output_min_addr + bit) - base] = (uint8_t) ((value >> bit) & 1u);

    int status = 0;
    if (write_bits_retry(ctx, base, span, bits, cfg->retries) != span)
    {
        fprintf(stderr, "testbench: write failed: %s\n", modbus_strerror(errno));
        status = 1;
    }
    else
    {
        for (int bit = lo; bit <= hi; bit++)
            if (mask & (1u << bit))
            {
                int         addr = cfg->output_min_addr + bit;
                const char* name = tb_config_output_label(cfg, addr);
                printf("  %-20s -> %s\n", name ? name : "?", (value & (1u << bit)) ? "ON" : "off");
            }
    }

    modbus_close(ctx);
    modbus_free(ctx);
    return status;
}

int tb_cli_iface(const TbConfig* cfg)
{
    int missing = 0;
    for (int i = 0; i < cfg->iface_count; i++)
    {
        bool found = tb_iface_detect(cfg->iface[i].port);
        printf("  %-10s %-32s %s\n", cfg->iface[i].name, cfg->iface[i].port, found ? "[ FOUND ]" : "[ NOT DETECTED ]");
        if (!found)
            missing++;
    }
    return missing ? 1 : 0;
}
