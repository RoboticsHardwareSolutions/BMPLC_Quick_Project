#pragma once

#include <stddef.h>

#include "config.h"
#include "state.h"

typedef struct TbModbus TbModbus;

/* Opens the RTU serial connection described by cfg->port/baudrate/timeout_s.
 * Returns NULL on failure, with a message written into errbuf. */
TbModbus* tb_modbus_open(const TbConfig* cfg, char* errbuf, size_t errbuf_len);
void      tb_modbus_close(TbModbus* m);

/* Reads the real coil state once at startup and seeds st->output_bits from it, so the
 * very first poll cycle doesn't stomp the hardware's actual state with zeros. */
int tb_modbus_seed_outputs(TbModbus* m, const TbConfig* cfg, TbState* st);

/* One poll cycle: read the input holding registers into st->input_bits, then
 * unconditionally rewrite the full output coil span from st->output_bits (this is what
 * keeps the modules' bus-error watchdog satisfied). Returns 0 if both transactions
 * succeeded, -1 otherwise (st->poll_errors is incremented internally either way). */
int tb_modbus_cycle(TbModbus* m, const TbConfig* cfg, TbState* st);
