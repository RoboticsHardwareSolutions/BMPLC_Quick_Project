#pragma once

/* Wire protocol for the low-latency NNG REQ/REP IPC API (testbench daemon <-> C/Python
 * clients). Deliberately label-free: a client resolves names against its own parse of
 * the same testbench.toml (see TbConfig / testbench_client.py's own tomllib use) and
 * only ever sends/receives bit positions and addresses over the wire.
 *
 * iface.* presence is intentionally NOT part of this protocol: it's a stateless
 * stat() check against paths already in testbench.toml, so a client can do it itself
 * without round-tripping through the daemon.
 *
 * All multi-byte fields are native-endian -- this is a localhost-only, same-machine
 * IPC transport (ipc:// = a Unix domain socket under the hood), not a network protocol.
 */

#include <stdint.h>

#define TB_PROTO_VERSION 1
#define TB_IPC_DEFAULT_URL "ipc:///tmp/testbench.ipc"
#define TB_IPC_MAX_FRAME 256

enum
{
    TB_OP_PING            = 0,
    TB_OP_GET_INPUTS      = 1,
    TB_OP_GET_OUTPUTS     = 2,
    TB_OP_SET_COILS_MASK = 3,
    TB_OP_GET_STATUS      = 4,
};

enum
{
    TB_STATUS_OK    = 0,
    TB_STATUS_ERROR = 1,
};

#pragma pack(push, 1)

typedef struct
{
    uint8_t version;
    uint8_t op;
    /* op-specific payload (if any) follows immediately */
} TbReqHeader;

typedef struct
{
    uint8_t version;
    uint8_t status;
    /* op-specific payload (if any) follows immediately; absent/ignored on error */
} TbRespHeader;

/* TB_OP_SET_COILS_MASK request payload.
 * Bit i of mask/value addresses coil (output_min_addr + i), i.e. relative to the
 * span TbConfig derives from io.map.outputs.labels -- the same addressing the
 * daemon's poll thread and TB_OP_GET_OUTPUTS use. Only bits set in `mask` are
 * applied; their new value is the corresponding bit of `value`. */
typedef struct
{
    uint32_t mask;
    uint32_t value;
} TbSetCoilsReq;

/* TB_OP_GET_INPUTS response payload. bit i = input bit index i (absolute, matches
 * testbench.toml's io.map.inputs.labels bit indices directly). */
typedef struct
{
    uint32_t bits;
    uint64_t ts_ms;
    uint8_t  valid;
} TbInputsResp;

/* TB_OP_GET_OUTPUTS response payload. bit i of `bits` = coil (min_addr + i). */
typedef struct
{
    uint32_t bits;
    int32_t  min_addr;
    int32_t  span;
} TbOutputsResp;

/* TB_OP_GET_STATUS response payload. */
typedef struct
{
    uint64_t uptime_ms;
    uint64_t poll_count;
    uint64_t poll_errors;
} TbStatusResp;

#pragma pack(pop)
