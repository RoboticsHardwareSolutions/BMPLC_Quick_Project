#pragma once

#include <stddef.h>
#include <stdint.h>

#define TB_MAX_LABELS 48
/* TbState.input_bits and the IPC wire protocol are a 32-bit mask, so at most 2
 * 16-bit holding registers can ever be packed into it -- this is not a tunable
 * buffer-size knob, raising it would silently overflow that 32-bit mask. */
#define TB_MAX_INPUT_REGS 2
#define TB_MAX_OUTPUT_SPAN 64
#define TB_MAX_IFACES 8

typedef struct
{
    int  index; /* input: bit index within the 32-bit mask; output: Modbus coil address */
    char name[32];
} TbLabel;

typedef struct
{
    char name[16];

    /* IOKit USB locationID (physical hub port) -- resolved to the adapter's current
     * /dev path at use time, since on macOS /dev/cu.usbserial-* names for cheap
     * USB-serial clones are not stable across reboots (see usb_resolve.h). */
    uint32_t usb_location;
} TbIface;

typedef struct
{
    /* [io.connection] */
    uint32_t usb_location; /* see TbIface.usb_location */
    int      inputs_id;
    int    outputs_id;
    int    baudrate;
    double timeout_s;
    int    retries; /* one-shot CLI transactions only -- the daemon's poll loop is its own retry */
    int    poll_interval_ms;

    /* [io.map.inputs] -- read as Holding Registers (FC 0x03) */
    int     input_start_address;
    int     input_count; /* number of 16-bit registers, clamped to TB_MAX_INPUT_REGS */
    TbLabel input_labels[TB_MAX_LABELS];
    int     input_label_count;

    /* [io.map.outputs] -- read/written as Coils (FC 0x01/0x05/0x0F).
     * NOTE: upstream io.py never actually uses io.map.outputs.start_address/count for
     * addressing -- only the label table's own keys are used as literal coil addresses.
     * We replicate that: the active address span is derived from output_labels, not
     * from the declared start_address/count (which are parsed but otherwise unused). */
    TbLabel output_labels[TB_MAX_LABELS];
    int     output_label_count;
    int     output_min_addr;
    int     output_span; /* clamped to TB_MAX_OUTPUT_SPAN */

    /* [iface.*] -- presence-only probes, each just a device path */
    TbIface iface[TB_MAX_IFACES];
    int     iface_count;
} TbConfig;

/* Parses `path` (testbench.toml) into *cfg. Returns 0 on success, -1 on failure
 * with a human-readable message written into errbuf. */
int tb_config_load(const char* path, TbConfig* cfg, char* errbuf, size_t errbuf_len);

const char* tb_config_input_label(const TbConfig* cfg, int bit_index);
const char* tb_config_output_label(const TbConfig* cfg, int addr);
int         tb_config_find_output_addr(const TbConfig* cfg, const char* label);

/* Packs up to TB_MAX_INPUT_REGS 16-bit holding registers (regs[0] = low 16 bits) into
 * the 32-bit mask used by TbState.input_bits and the IPC wire protocol. n beyond
 * TB_MAX_INPUT_REGS is ignored rather than shifted, which would be undefined behavior. */
uint32_t tb_regs_to_input_bits(const uint16_t* regs, int n);
