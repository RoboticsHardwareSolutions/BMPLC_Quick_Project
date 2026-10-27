#pragma once

#include <stdint.h>

#include "config.h"

/* One-shot, direct (no running daemon) Modbus sessions: open, transact, close --
 * mirrors today's testbench/cli.py behaviour. Each returns 0 on success, non-zero
 * on failure (suitable as a process exit code). */

int tb_cli_list(const TbConfig* cfg);
int tb_cli_read(const TbConfig* cfg);

/* `assignments` is "LABEL=0|1[,LABEL=0|1...]"; label names are resolved against
 * cfg->output_labels (i.e. straight from testbench.toml, nothing hardcoded). */
int tb_cli_write(const TbConfig* cfg, const char* assignments);

int tb_cli_iface(const TbConfig* cfg);

/* Parses "LABEL=0|1[,LABEL=0|1...]" into a (mask, value) pair relative to
 * cfg->output_min_addr (bit i of mask/value <-> coil output_min_addr + i) -- the same
 * addressing TB_OP_SET_COILS_MASK uses over IPC. Shared by tb_cli_write's direct-session
 * path and main.c's daemon-routed IPC path, so both accept exactly the same syntax.
 * Returns 0 on success, non-zero (with an error already printed to stderr) on failure. */
int tb_parse_write_assignments(const TbConfig* cfg, const char* assignments, uint32_t* out_mask, uint32_t* out_value);
