/*
 * Example: ask a running testbench daemon whether one [iface.*] interface
 * (canbus/rs422/rs485/rs232) is available right now.
 *
 * tb_client_iface_available() returns false uniformly whether the daemon didn't
 * respond, the interface isn't configured in this stand's testbench.toml, or it's
 * configured but not currently detected -- other test utilities are expected to treat
 * all three the same way: this interface isn't usable right now.
 *
 * Build & run (from testbench/io_hub/):
 *   mkdir -p build && cd build && cmake .. && cmake --build . --target example_check_iface
 *   ./example_check_iface canbus
 *
 * Prerequisite: a testbench daemon must already be running, e.g.:
 *   ./testbench --config ../../testbench.toml
 */
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "testbench_client.h"
#include "testbench_proto.h"

/* Reverse lookup against the canonical TB_IFACE_* <-> name table in
 * testbench_proto.h, rather than a second hand-maintained copy of it here. */
static bool iface_from_name(const char* name, TbIfaceId* out_iface)
{
    for (int id = TB_IFACE_CANBUS; id <= TB_IFACE_RS232; id++)
    {
        const char* known = tb_iface_name((TbIfaceId) id);
        if (known && strcmp(name, known) == 0)
        {
            *out_iface = (TbIfaceId) id;
            return true;
        }
    }
    return false;
}

int main(int argc, char** argv)
{
    if (argc != 2)
    {
        fprintf(stderr, "usage: %s <canbus|rs422|rs485|rs232>\n", argv[0]);
        return 1;
    }

    TbIfaceId iface;
    if (!iface_from_name(argv[1], &iface))
    {
        fprintf(stderr, "unknown interface '%s' (expected canbus|rs422|rs485|rs232)\n", argv[1]);
        return 1;
    }

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

    char path[128];
    bool available = tb_client_iface_available(client, iface, path, sizeof(path));
    if (available)
        printf("%s: available (%s)\n", argv[1], path);
    else
        printf("%s: not available\n", argv[1]);

    tb_client_close(client);
    return available ? 0 : 1;
}
