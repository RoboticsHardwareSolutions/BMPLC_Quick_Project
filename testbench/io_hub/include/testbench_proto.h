#pragma once

/* Wire protocol for the low-latency NNG REQ/REP IPC API (testbench daemon <-> C/Python
 * clients). Deliberately label-free: a client resolves names against its own parse of
 * the same testbench.toml (see TbConfig / testbench_client.py's own tomllib use) and
 * only ever sends/receives bit positions and addresses over the wire.
 *
 * iface.* presence IS part of this protocol, but narrowly: TB_OP_GET_IFACE_STATUS
 * answers "is this one specific interface available right now?" for one of the four
 * well-known interface kinds (TB_IFACE_*), nothing more. A client-side stat() check
 * can't tell "device unplugged" apart from "daemon not running", and other test
 * utilities need that distinction collapsed into a single answer -- which only a
 * daemon-routed call can give. There's deliberately no "list all interfaces" call:
 * callers already know which of the four kinds they care about.
 *
 * All multi-byte fields are native-endian -- this is a localhost-only, same-machine
 * IPC transport (ipc:// = a Unix domain socket under the hood), not a network protocol.
 */

#include <stddef.h>
#include <stdint.h>

#define TB_PROTO_VERSION 1
#define TB_IPC_DEFAULT_URL "ipc:///tmp/testbench.ipc"
#define TB_IPC_MAX_FRAME 256

enum
{
    TB_OP_PING             = 0,
    TB_OP_GET_INPUTS       = 1,
    TB_OP_GET_OUTPUTS      = 2,
    TB_OP_SET_COILS_MASK   = 3,
    TB_OP_GET_STATUS       = 4,
    TB_OP_GET_IFACE_STATUS = 5,
};

enum
{
    TB_STATUS_OK    = 0,
    TB_STATUS_ERROR = 1,
};

/* The four well-known [iface.*] interface kinds TB_OP_GET_IFACE_STATUS can ask about.
 * Not every testbench.toml configures all four -- one that's absent from this stand's
 * config answers "not present" (TB_STATUS_OK, present=0), same as one that's
 * configured but not currently plugged in; only a value outside this enum is a
 * protocol error (TB_STATUS_ERROR). Named (not anonymous) so client APIs can take a
 * TbIfaceId parameter instead of a bare int. */
typedef enum
{
    TB_IFACE_CANBUS = 0,
    TB_IFACE_RS422  = 1,
    TB_IFACE_RS485  = 2,
    TB_IFACE_RS232  = 3,
} TbIfaceId;

/* Canonical TB_IFACE_* <-> [iface.<name>] TOML key name mapping -- the one place this
 * is spelled out, shared by the daemon (ipc_server.c) and any other C code that needs
 * to go from one to the other (e.g. a CLI/example argument parser). Returns NULL for
 * a value outside the enum. */
static inline const char* tb_iface_name(TbIfaceId id)
{
    switch (id)
    {
        case TB_IFACE_CANBUS: return "canbus";
        case TB_IFACE_RS422:  return "rs422";
        case TB_IFACE_RS485:  return "rs485";
        case TB_IFACE_RS232:  return "rs232";
    }
    return NULL;
}

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

/* TB_OP_GET_IFACE_STATUS request payload. `iface` is one of the TB_IFACE_* values. */
typedef struct
{
    uint8_t iface;
} TbIfaceStatusReq;

/* TB_OP_GET_IFACE_STATUS response payload. `path` is the resolved /dev/cu.* path
 * (NUL-terminated) when present=1; an empty string when present=0, for any reason
 * (not currently plugged in, not configured in this stand's testbench.toml, daemon
 * unreachable never reaches this struct at all). 64 must match TB_IFACE_PATH_LEN in
 * src/config.h, which TbState.iface_path[]'s entries are sized to. */
typedef struct
{
    uint8_t present;
    char    path[64];
} TbIfaceStatusResp;

#pragma pack(pop)
