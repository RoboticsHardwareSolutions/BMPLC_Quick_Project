#include "config.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "tomlc17.h"

static void copy_tstr(toml_datum_t d, char* dst, size_t cap)
{
    dst[0] = '\0';
    if (d.type != TOML_STRING || cap == 0)
        return;
    int n = d.u.str.len;
    if (n < 0)
        n = 0;
    if ((size_t) n >= cap)
        n = (int) cap - 1;
    memcpy(dst, d.u.str.ptr, (size_t) n);
    dst[n] = '\0';
}

static long get_int(toml_datum_t table, const char* key, long def)
{
    toml_datum_t d = toml_get(table, key);
    if (d.type == TOML_INT64)
        return (long) d.u.int64;
    return def;
}

static double get_dbl(toml_datum_t table, const char* key, double def)
{
    toml_datum_t d = toml_get(table, key);
    if (d.type == TOML_FP64)
        return d.u.fp64;
    if (d.type == TOML_INT64)
        return (double) d.u.int64;
    return def;
}

/* 0 means "key absent" -- never a valid IOKit locationID (0 is the host controller
 * itself in the registry, not a leaf USB-serial device). */
static uint32_t get_uint32(toml_datum_t table, const char* key)
{
    toml_datum_t d = toml_get(table, key);
    if (d.type == TOML_INT64)
        return (uint32_t) d.u.int64;
    return 0;
}

/* `labels_table` is a TOML table whose keys are decimal-string indices/addresses and
 * whose values are label name strings -- the shared shape of both
 * io.map.inputs.labels and io.map.outputs.labels. */
static int load_labels(toml_datum_t labels_table, TbLabel* out, int max)
{
    int n = 0;
    if (labels_table.type != TOML_TABLE)
        return 0;
    for (int i = 0; i < labels_table.u.tab.size && n < max; i++)
    {
        toml_datum_t val = labels_table.u.tab.value[i];
        if (val.type != TOML_STRING)
            continue;
        out[n].index = atoi(labels_table.u.tab.key[i]);
        copy_tstr(val, out[n].name, sizeof(out[n].name));
        n++;
    }
    return n;
}

int tb_config_load(const char* path, TbConfig* cfg, char* errbuf, size_t errbuf_len)
{
    memset(cfg, 0, sizeof(*cfg));

    toml_result_t r = toml_parse_file_ex(path);
    if (!r.ok)
    {
        snprintf(errbuf, errbuf_len, "%s", r.errmsg);
        toml_free(r);
        return -1;
    }

    toml_datum_t conn = toml_seek(r.toptab, "io.connection");
    if (conn.type != TOML_TABLE)
    {
        snprintf(errbuf, errbuf_len, "missing [io.connection] table in %s", path);
        toml_free(r);
        return -1;
    }
    cfg->usb_location = get_uint32(conn, "usb_location");
    cfg->inputs_id  = (int) get_int(conn, "inputs_id", 1);
    /* "ouputs_id" (missing 't') is the key actually used in testbench.toml and io.py --
     * kept verbatim here so this daemon reads the same config file unmodified. */
    cfg->outputs_id       = (int) get_int(conn, "ouputs_id", 2);
    cfg->baudrate          = (int) get_int(conn, "baudrate", 115200);
    cfg->timeout_s          = get_dbl(conn, "timeout", 1.0);
    cfg->retries            = (int) get_int(conn, "retries", 3);
    cfg->poll_interval_ms  = (int) get_int(conn, "poll_interval_ms", 200);

    toml_datum_t in_map = toml_seek(r.toptab, "io.map.inputs");
    cfg->input_start_address = (int) get_int(in_map, "start_address", 0);
    cfg->input_count          = (int) get_int(in_map, "count", 2);
    if (cfg->input_count > TB_MAX_INPUT_REGS)
    {
        fprintf(stderr,
                "testbench: warning: io.map.inputs.count=%d exceeds the 32-bit input mask's "
                "capacity (%d registers max), clamping\n",
                cfg->input_count,
                TB_MAX_INPUT_REGS);
        cfg->input_count = TB_MAX_INPUT_REGS;
    }
    cfg->input_label_count = load_labels(toml_get(in_map, "labels"), cfg->input_labels, TB_MAX_LABELS);

    toml_datum_t out_map    = toml_seek(r.toptab, "io.map.outputs");
    cfg->output_label_count = load_labels(toml_get(out_map, "labels"), cfg->output_labels, TB_MAX_LABELS);

    if (cfg->output_label_count > 0)
    {
        int lo = cfg->output_labels[0].index, hi = lo;
        for (int i = 1; i < cfg->output_label_count; i++)
        {
            if (cfg->output_labels[i].index < lo)
                lo = cfg->output_labels[i].index;
            if (cfg->output_labels[i].index > hi)
                hi = cfg->output_labels[i].index;
        }
        cfg->output_min_addr = lo;
        cfg->output_span       = hi - lo + 1;
        if (cfg->output_span > TB_MAX_OUTPUT_SPAN)
        {
            fprintf(stderr,
                    "testbench: warning: output label span %d exceeds compiled-in max %d, clamping\n",
                    cfg->output_span,
                    TB_MAX_OUTPUT_SPAN);
            cfg->output_span = TB_MAX_OUTPUT_SPAN;
        }
    }

    toml_datum_t iface = toml_seek(r.toptab, "iface");
    if (iface.type == TOML_TABLE)
    {
        for (int i = 0; i < iface.u.tab.size && cfg->iface_count < TB_MAX_IFACES; i++)
        {
            toml_datum_t sub = iface.u.tab.value[i];
            if (sub.type != TOML_TABLE)
                continue;
            TbIface* slot = &cfg->iface[cfg->iface_count++];
            const char* name = iface.u.tab.key[i];
            size_t      n    = strlen(name);
            if (n >= sizeof(slot->name))
                n = sizeof(slot->name) - 1;
            memcpy(slot->name, name, n);
            slot->name[n] = '\0';
            slot->usb_location = get_uint32(sub, "usb_location");
        }
    }

    toml_free(r);
    return 0;
}

const char* tb_config_input_label(const TbConfig* cfg, int bit_index)
{
    for (int i = 0; i < cfg->input_label_count; i++)
        if (cfg->input_labels[i].index == bit_index)
            return cfg->input_labels[i].name;
    return NULL;
}

const char* tb_config_output_label(const TbConfig* cfg, int addr)
{
    for (int i = 0; i < cfg->output_label_count; i++)
        if (cfg->output_labels[i].index == addr)
            return cfg->output_labels[i].name;
    return NULL;
}

int tb_config_find_output_addr(const TbConfig* cfg, const char* label)
{
    for (int i = 0; i < cfg->output_label_count; i++)
        if (strcmp(cfg->output_labels[i].name, label) == 0)
            return cfg->output_labels[i].index;
    return -1;
}

uint32_t tb_bits_to_input_mask(const uint8_t* bits, int n)
{
    if (n > TB_MAX_INPUT_BITS)
        n = TB_MAX_INPUT_BITS;
    uint32_t mask = 0;
    for (int i = 0; i < n; i++)
        if (bits[i])
            mask |= 1u << i;
    return mask;
}
