/*
 * Example: toggle one output coil by its testbench.toml label name.
 *
 * Unlike 01_read_inputs.c, this links against the daemon's own config.c (+ tomlc17)
 * to parse testbench.toml and resolve a label name to a bit position -- exactly what
 * testbench_client.py's TestbenchLabels does on the Python side, and the approach a
 * real application should take, since the wire protocol itself is deliberately
 * label-free (see testbench/io_hub/include/testbench_proto.h).
 *
 * Build & run (from testbench/io_hub/):
 *   mkdir -p build && cd build && cmake .. && cmake --build . --target example_toggle_output
 *   ./example_toggle_output USB_EMPTY ../../testbench.toml
 *
 * Prerequisite: a testbench daemon must already be running, e.g.:
 *   ./testbench --config ../../testbench.toml
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include "config.h"
#include "testbench_client.h"

int main(int argc, char** argv)
{
    if (argc < 3)
    {
        fprintf(stderr, "usage: %s LABEL path/to/testbench.toml\n", argv[0]);
        return 2;
    }
    const char* label       = argv[1];
    const char* config_path = argv[2];

    TbConfig cfg;
    char     errbuf[256];
    if (tb_config_load(config_path, &cfg, errbuf, sizeof(errbuf)) != 0)
    {
        fprintf(stderr, "failed to load %s: %s\n", config_path, errbuf);
        return 1;
    }

    int addr = tb_config_find_output_addr(&cfg, label);
    if (addr < 0)
    {
        fprintf(stderr, "'%s' is not a known output label (see testbench.toml's io.map.outputs.labels)\n", label);
        return 1;
    }
    /* TB_OP_SET_COILS_MASK addresses coils relative to output_min_addr, in a uint32_t
     * mask -- the same 32-coil limit testbench_client.py's build_coil_request() enforces. */
    int bit = addr - cfg.output_min_addr;
    if (bit < 0 || bit >= 32)
    {
        fprintf(stderr, "'%s' is outside the 32-coil span this protocol can address\n", label);
        return 1;
    }

    TbClient* client = tb_client_connect(NULL);
    if (!client || !tb_client_ping(client))
    {
        fprintf(stderr, "testbench daemon not reachable\n");
        if (client)
            tb_client_close(client);
        return 1;
    }

    uint32_t out_bits = 0;
    int32_t  min_addr = 0, span = 0;
    if (!tb_client_get_outputs(client, &out_bits, &min_addr, &span))
    {
        fprintf(stderr, "get_outputs failed\n");
        tb_client_close(client);
        return 1;
    }
    bool before = ((out_bits >> bit) & 1u) != 0;
    printf("%s: %s -> %s\n", label, before ? "ON" : "off", before ? "off" : "ON");

    uint32_t mask  = (1u << bit);
    uint32_t value = before ? 0u : mask;
    if (!tb_client_set_coils_mask(client, mask, value))
    {
        fprintf(stderr, "set_coils_mask failed\n");
        tb_client_close(client);
        return 1;
    }

    tb_client_get_outputs(client, &out_bits, &min_addr, &span);
    bool after = ((out_bits >> bit) & 1u) != 0;
    printf("confirmed: %s is now %s\n", label, after ? "ON" : "off");

    tb_client_close(client);
    return 0;
}
