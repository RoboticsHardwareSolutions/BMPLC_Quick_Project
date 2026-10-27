#pragma once

#include "config.h"
#include "state.h"

typedef struct TbHttp TbHttp;

/* Starts the HTTP control panel (static files from web_root + the REST API below) on
 * its own thread. Returns NULL on failure. */
TbHttp* tb_http_start(const TbConfig* cfg, TbState* st, const char* web_root, const char* listen_url);
void    tb_http_stop(TbHttp* http);

/*
 * REST API:
 *   GET  /api/state    -> {"inputs":{label:bool,...},"outputs":{label:bool,...},
 *                           "iface":{name:bool,...},
 *                           "status":{"input_valid":bool,"input_age_ms":N,
 *                                     "poll_count":N,"poll_errors":N,"uptime_ms":N}}
 *   POST /api/outputs  <- {"LABEL": true|false, ...} (any subset of output labels);
 *                          merges into the shared desired-state cache the Modbus poll
 *                          thread writes out every cycle.
 *   *                  -> static files from web_root (web/index.html, style.css, app.js)
 */
