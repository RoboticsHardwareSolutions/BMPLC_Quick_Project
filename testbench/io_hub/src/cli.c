#include "cli.h"

#include <errno.h>
#include <modbus.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "iface_scan.h"
#include "modbus_io.h"

int tb_cli_list(const TbConfig* cfg)
{
    printf("Inputs (discrete inputs, slave %d, bit index -> label):\n", cfg->inputs_id);
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
    modbus_t* ctx = tb_modbus_open_ctx(cfg, errbuf, sizeof(errbuf));
    if (!ctx)
    {
        fprintf(stderr, "testbench: %s\n", errbuf);
        return 1;
    }

    modbus_set_slave(ctx, cfg->inputs_id);
    uint8_t bits_in[TB_MAX_INPUT_BITS] = {0};
    int     n_bits                     = cfg->input_count * 16;
    int     rc = tb_modbus_read_input_bits_retry(ctx, cfg->input_start_address, n_bits, bits_in, cfg->retries);

    int status = 0;
    if (rc != n_bits)
    {
        fprintf(stderr, "testbench: read failed: %s\n", modbus_strerror(errno));
        status = 1;
    }
    else
    {
        uint32_t bits = tb_bits_to_input_mask(bits_in, n_bits);
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
    modbus_t* ctx = tb_modbus_open_ctx(cfg, errbuf, sizeof(errbuf));
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
    if (tb_modbus_read_bits_retry(ctx, base, span, bits, cfg->retries) != span)
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
    if (tb_modbus_write_bits_retry(ctx, base, span, bits, cfg->retries) != span)
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
        char path[TB_IFACE_PATH_LEN];
        bool found = tb_iface_detect(&cfg->iface[i], path, sizeof(path));
        if (!found)
            strcpy(path, "(not attached)");
        printf("  %-10s loc=0x%-8x %-28s %s\n",
               cfg->iface[i].name,
               cfg->iface[i].usb_location,
               path,
               found ? "[ FOUND ]" : "[ NOT DETECTED ]");
        if (!found)
            missing++;
    }
    return missing ? 1 : 0;
}
