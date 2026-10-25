#pragma once

#include <stdbool.h>
#include <stdint.h>

/* Low-latency C client for the testbench daemon's NNG REQ/REP IPC API
 * (testbench/include/testbench_proto.h). Connects to an already-running daemon;
 * does not touch the serial port itself.
 *
 * Label names are NOT part of this API -- resolve them against your own parse of
 * testbench.toml (same file the daemon reads) and work in bit positions /
 * coil addresses, exactly like testbench_proto.h's wire format does. */

typedef struct TbClient TbClient;

/* `url` may be NULL to use the daemon's default (ipc:///tmp/testbench.ipc).
 * Returns NULL if the socket can't even be created/dialed -- this does NOT confirm a
 * daemon is actually listening; call tb_client_ping() for that. */
TbClient* tb_client_connect(const char* url);
void      tb_client_close(TbClient* c);

/* Every call below returns false on any failure (no daemon, timeout, bad response) and
 * leaves out-parameters untouched. Each call has its own short send/recv timeout, so
 * none of these block indefinitely if the daemon has gone away. */
bool tb_client_ping(TbClient* c);
bool tb_client_get_inputs(TbClient* c, uint32_t* bits, uint64_t* ts_ms, bool* valid);
bool tb_client_get_outputs(TbClient* c, uint32_t* bits, int32_t* min_addr, int32_t* span);
bool tb_client_set_coils_mask(TbClient* c, uint32_t mask, uint32_t value);
bool tb_client_get_status(TbClient* c, uint64_t* uptime_ms, uint64_t* poll_count, uint64_t* poll_errors);
