#pragma once

#include <stdbool.h>
#include <stdint.h>

/* Low-latency C client for the testbench daemon's NNG REQ/REP IPC API
 * (testbench/io_hub/include/testbench_proto.h). Connects to an already-running
 * daemon; does not touch the serial port itself.
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

/* Every call below returns false on any failure and leaves out-parameters untouched.
 * Each call has its own short send/recv timeout, so none of these block indefinitely
 * if the daemon has gone away. "Failure" covers two distinct situations:
 *   - the daemon is unreachable (not running, timeout, malformed response), or
 *   - the daemon is reachable but its Modbus link to the hardware is currently down
 *     (get_inputs/get_outputs: the last poll of that direction didn't actually reach
 *     the bus, so there's no trustworthy data to hand back; set_coils_mask: the write
 *     would never reach the hardware, so the daemon rejects it outright instead of
 *     silently queuing it).
 * tb_client_get_status() and tb_client_ping() are NOT gated on Modbus health -- they
 * stay available specifically so a caller can diagnose *why* the others are failing. */
bool tb_client_ping(TbClient* c);
bool tb_client_get_inputs(TbClient* c, uint32_t* bits, uint64_t* ts_ms, bool* valid);
bool tb_client_get_outputs(TbClient* c, uint32_t* bits, int32_t* min_addr, int32_t* span);
bool tb_client_set_coils_mask(TbClient* c, uint32_t mask, uint32_t value);
bool tb_client_get_status(TbClient* c, uint64_t* uptime_ms, uint64_t* poll_count, uint64_t* poll_errors);
