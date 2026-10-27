/*
 * Example: connect to a running testbench daemon and print the raw 32-bit input mask.
 *
 * This is the minimal form of the C API: no label resolution, no TOML parsing -- just
 * testbench_client.h talking straight to the daemon over NNG IPC. See
 * 02_toggle_output.c for an example that also resolves label names from
 * testbench.toml, the way a real application should.
 *
 * Build & run (from testbench/io_hub/):
 *   mkdir -p build && cd build && cmake .. && cmake --build . --target example_read_inputs
 *   ./example_read_inputs
 *
 * Prerequisite: a testbench daemon must already be running, e.g.:
 *   ./testbench --config ../../testbench.toml
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include "testbench_client.h"

int main(void)
{
    TbClient* client = tb_client_connect(NULL); /* NULL -> default ipc:///tmp/testbench.ipc */
    if (!client)
    {
        fprintf(stderr, "could not create IPC client\n");
        return 1;
    }

    if (!tb_client_ping(client))
    {
        fprintf(stderr, "testbench daemon not reachable\n");
        tb_client_close(client);
        return 1;
    }

    uint32_t bits  = 0;
    uint64_t ts_ms = 0;
    bool     valid = false;
    if (!tb_client_get_inputs(client, &bits, &ts_ms, &valid))
    {
        fprintf(stderr, "get_inputs failed\n");
        tb_client_close(client);
        return 1;
    }

    printf("inputs = 0x%08x  (valid=%s, daemon snapshot ts_ms=%llu)\n", bits, valid ? "true" : "false", (unsigned long long) ts_ms);
    for (int bit = 0; bit < 32; bit++)
        if (bits & (1u << bit))
            printf("  bit %2d is ON\n", bit);

    tb_client_close(client);
    return 0;
}
