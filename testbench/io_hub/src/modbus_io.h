#pragma once

#include <stddef.h>

#include <modbus.h>

#include "config.h"
#include "state.h"

typedef struct TbModbus TbModbus;

/* Opens the RTU serial connection at cfg->usb_location (resolved via usb_resolve.h to
 * its current /dev path)/baudrate/timeout_s. Returns NULL on failure, with a message
 * written into errbuf. */
TbModbus* tb_modbus_open(const TbConfig* cfg, char* errbuf, size_t errbuf_len);
void      tb_modbus_close(TbModbus* m);

/* Same connection setup as tb_modbus_open(), but returns the raw libmodbus context
 * instead of a persistent TbModbus -- for one-shot direct sessions (the CLI's
 * --read/--write/--list path) that open, transact once, and close right away. Caller
 * owns the result (modbus_close()+modbus_free() when done). Returns NULL on failure,
 * with a message written into errbuf. */
modbus_t* tb_modbus_open_ctx(const TbConfig* cfg, char* errbuf, size_t errbuf_len);

/* Retries a single transaction up to `attempts` times (a short delay between tries) --
 * shared by one-shot CLI sessions and the daemon's startup output-state seed read,
 * neither of which has a next poll cycle to fall back on the way tb_modbus_cycle()'s
 * ongoing polling does if a transaction hits transient RS485 bus noise. Returns the
 * underlying libmodbus call's return value from the last attempt. */
int tb_modbus_read_registers_retry(modbus_t* ctx, int addr, int n, uint16_t* dest, int attempts);
int tb_modbus_read_bits_retry(modbus_t* ctx, int addr, int n, uint8_t* dest, int attempts);
int tb_modbus_write_bits_retry(modbus_t* ctx, int addr, int n, const uint8_t* data, int attempts);

/* Closes and reopens the serial connection in place (m stays valid). Needed to recover
 * after the serial device drops out and comes back -- the existing fd doesn't resurrect
 * itself when the port reappears. Returns 0 on success, -1 on failure (errbuf set). */
int tb_modbus_reconnect(TbModbus* m, const TbConfig* cfg, char* errbuf, size_t errbuf_len);

/* Reads the real coil state once at startup and seeds st->output_bits from it, so the
 * very first poll cycle doesn't stomp the hardware's actual state with zeros. */
int tb_modbus_seed_outputs(TbModbus* m, const TbConfig* cfg, TbState* st);

/* One poll cycle: read the input holding registers into st->input_bits, then
 * unconditionally rewrite the full output coil span from st->output_bits (this is what
 * keeps the modules' bus-error watchdog satisfied). Returns 0 if both transactions
 * succeeded, -1 otherwise (st->poll_errors is incremented internally either way). */
int tb_modbus_cycle(TbModbus* m, const TbConfig* cfg, TbState* st);
