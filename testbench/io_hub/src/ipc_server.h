#pragma once

#include "config.h"
#include "state.h"

typedef struct TbIpc TbIpc;

/* Starts the NNG REP server on `url` (default TB_IPC_DEFAULT_URL) on its own thread.
 * Returns NULL on failure. */
TbIpc* tb_ipc_start(const TbConfig* cfg, TbState* st, const char* url);
void   tb_ipc_stop(TbIpc* ipc);
