#pragma once
#include "rhs.h"
#include "rhs_hal.h"
#include "rhs_version.h"
#include "mongoose.h"
#include <stdio.h>
#if defined(RHS_SERVICE_USB_SERIAL_BRIDGE)
#include "usb_serial_bridge.h"
#endif
#if defined(RHS_APPLICATION_USB_ETH_BRIDGE)
#include "usb_eth_bridge.h"
#endif

static inline void io_relay_write(size_t index, bool on)
{
    if (index > 4)
        return;

    if (index == 0)
        on ? KEY0_ON() : KEY0_OFF();
    else if (index == 1)
        on ? KEY1_ON() : KEY1_OFF();
    else if (index == 2)
        on ? KEY2_ON() : KEY2_OFF();
    else if (index == 3)
        on ? KEY3_ON() : KEY3_OFF();
    else
        on ? KEY4_ON() : KEY4_OFF();
}

static inline void io_out_write(size_t index, bool on)
{
    if (index > 4)
        return;

    if (index == 0)
        on ? OUT0_ON() : OUT0_OFF();
    else if (index == 1)
        on ? OUT1_ON() : OUT1_OFF();
    else if (index == 2)
        on ? OUT2_ON() : OUT2_OFF();
    else if (index == 3)
        on ? OUT3_ON() : OUT3_OFF();
    else
        on ? OUT4_ON() : OUT4_OFF();
}

// Appends 'count' boolean values as a JSON array fragment (without brackets),
// returns the new offset.
static inline size_t io_json_bools(char* buf, size_t size, size_t off, const bool* values, size_t count)
{
    for (size_t i = 0; i < count; i++)
        off += mg_snprintf(buf + off, size - off, "%s%s", (i > 0) ? "," : "", values[i] ? "true" : "false");
    return off;
}

static inline void http_fn(struct mg_connection* c, int ev, void* ev_data)
{
    if (ev == MG_EV_HTTP_MSG)
    {
        struct mg_http_message* hm = (struct mg_http_message*) ev_data;
        if (mg_match(hm->uri, mg_str("/api/info"), NULL))
        {
            if (!mg_strcmp(hm->method, mg_str("GET")))
            {
                const uint8_t* uid = rhs_hal_version_uid();
                char           uid_str[28];
                sprintf(uid_str,
                        "%02X%02X-%02X%02X-%02X%02X%02X%02X-%02X%02X%02X%02X",
                        uid[0],
                        uid[1],  // 16 - bit
                        uid[2],
                        uid[3],  // 16 - bit
                        uid[4],
                        uid[5],
                        uid[6],
                        uid[7],  // 32 - bits
                        uid[8],
                        uid[9],
                        uid[10],
                        uid[11]  // 32 - bits
                );
                char v_str[10];
                sprintf(v_str, "v%d.%d.%d", PROJECT_VERSION_MAJOR, PROJECT_VERSION_MINOR, PROJECT_VERSION_PATCH);
                mg_http_reply(c,
                              200,
                              "Content-Type: application/json\r\n",
                              "{%m:%m, %m:%m, %m:%m}",
                              MG_ESC("serial"),
                              MG_ESC(uid_str),
                              MG_ESC("bmplcType"),
#if defined(BMPLC_M)
                              MG_ESC("BMPLC_M"),
#elif defined(BMPLC_XL)
                              MG_ESC("BMPLC_XL"),
#else
                              MG_ESC("Custom"),
#endif
                              MG_ESC("version"),
                              MG_ESC(v_str));
            }
        }
        else if (mg_match(hm->uri, mg_str("/api/tasks"), NULL))
        {
            if (!mg_strcmp(hm->method, mg_str("GET")))
            {
                static RHSThreadList* thread_list = NULL;
                if (!thread_list)
                    thread_list = rhs_thread_list_create();

                uint16_t count;

                rhs_thread_enumerate(thread_list);
                count = rhs_thread_list_size(thread_list);

                static char body[1024];  // Save stack
                size_t      off = 0;

                for (size_t i = 0; i < count; i++)
                {
                    RHSThreadListItem* item = rhs_thread_list_at(thread_list, i);

                    if (sizeof(body) - off < 64)
                        break;

                    off += mg_snprintf(body + off,
                                       sizeof(body) - off,
                                       "%s{%m:%m, %m:%u, %m:%f, %m:%u}",
                                       (i > 0) ? "," : "",
                                       MG_ESC("task"),
                                       MG_ESC(item->name),
                                       MG_ESC("priority"),
                                       item->priority,
                                       MG_ESC("load"),
                                       item->cpu,
                                       MG_ESC("stackMinFree"),
                                       item->stack_min_free);
                }

                // rhs_thread_list_destroy(thread_list);
                mg_http_reply(c, 200, "Content-Type: application/json\r\n", "{%m:[%s]}", MG_ESC("tasks"), body);
            }
        }
        else if (mg_match(hm->uri, mg_str("/api/bridges"), NULL))
        {
            if (!mg_strcmp(hm->method, mg_str("GET")))
            {
                static char body[1024];  // Save stack
                size_t      off = 0;

#if defined(RHS_SERVICE_USB_SERIAL_BRIDGE)
                off += mg_snprintf(body + off, sizeof(body) - off, "%s{\"usb\":\"rs232\"}", (off > 0) ? "," : "");
                off += mg_snprintf(body + off, sizeof(body) - off, "%s{\"usb\":\"rs485\"}", (off > 0) ? "," : "");
                off += mg_snprintf(body + off, sizeof(body) - off, "%s{\"rs232\":\"rs485\"}", (off > 0) ? "," : "");
#endif
#if defined(RHS_APPLICATION_USB_ETH_BRIDGE)
                off += mg_snprintf(body + off, sizeof(body) - off, "%s{\"usb\":\"eth\"}", (off > 0) ? "," : "");
#endif
                off += mg_snprintf(body + off, sizeof(body) - off, "%s{\"usb\":\"can\"}", (off > 0) ? "," : "");
                if (off != 0)
                    mg_http_reply(c, 200, "Content-Type: application/json\r\n", "{%m:[%s]}", MG_ESC("bridges"), body);
                else
                    mg_http_reply(c, 204, "Content-Type: 0\r\n", "");
            }
            else if (!mg_strcmp(hm->method, mg_str("POST")))
            {
                int           poff  = 0;
                int           plen  = 0;
                int           toff  = 0;
                int           tlen  = 0;
                struct mg_str port  = mg_str_n("", 0);
                struct mg_str type  = mg_str_n("", 0);

                poff = mg_json_get(hm->body, "$.port", &plen);
                if (poff >= 0 && plen >= 2 && hm->body.buf != NULL && (size_t) poff + (size_t) plen <= hm->body.len &&
                    hm->body.buf[poff] == '"')
                {
                    port = mg_str_n(hm->body.buf + poff + 1, (size_t) plen - 2);
                }

                toff = mg_json_get(hm->body, "$.type", &tlen);
                if (toff >= 0 && tlen >= 2 && hm->body.buf != NULL && (size_t) toff + (size_t) tlen <= hm->body.len &&
                    hm->body.buf[toff] == '"')
                {
                    type = mg_str_n(hm->body.buf + toff + 1, (size_t) tlen - 2);
                }

                if (!mg_strcmp(port, mg_str("usb")) && !mg_strcmp(type, mg_str("rs232")))
                {
#if defined(RHS_SERVICE_USB_SERIAL_BRIDGE)
                    UsbSerialConfig cfg = {
                        .vcp_ch         = 0,
                        .serial_ch      = RHSHalSerialIdRS232,
                        .flow_pins      = 0,
                        .baudrate_mode  = 0,
                        .baudrate       = 9600,
                        .software_de_re = 0,
                    };
                    (void) usb_serial_enable(&cfg);
#endif
                }

                if (!mg_strcmp(port, mg_str("usb")) && !mg_strcmp(type, mg_str("eth")))
                {
#if defined(RHS_APPLICATION_USB_ETH_BRIDGE)
                    (void) usb_eth_bridge_start(NULL);
#endif
                }

                mg_http_reply(c, 200, "Content-Type: application/json\r\n", "{%m:%s}", MG_ESC("ok"), "true");
            }
        }
        else if (mg_match(hm->uri, mg_str("/api/io"), NULL))
        {
            if (!mg_strcmp(hm->method, mg_str("GET")))
            {
                // Bitmask: bits 0-4 inputs, bits 5-9 relays, bits 10-14 outputs
                const bool d_i[5] = {IN0_IS_HIGH(), IN1_IS_HIGH(), IN2_IS_HIGH(), IN3_IS_HIGH(), IN4_IS_HIGH()};
                const bool d_o[5] = {OUT0_IS_HIGH(), OUT1_IS_HIGH(), OUT2_IS_HIGH(), OUT3_IS_HIGH(), OUT4_IS_HIGH()};
                const bool rel[5] = {KEY0_IS_OPEN(), KEY1_IS_OPEN(), KEY2_IS_OPEN(), KEY3_IS_OPEN(), KEY4_IS_OPEN()};
                bool       states[15];

                for (int i = 0; i < 5; i++)
                    states[i] = d_i[i];
                for (int i = 0; i < 5; i++)
                    states[5 + i] = rel[i];
                for (int i = 0; i < 5; i++)
                    states[10 + i] = d_o[i];

                unsigned mask = 0;
                for (int i = 0; i < 15; i++)
                    if (states[i])
                        mask |= (1u << i);

                mg_http_reply(c, 200, "Content-Type: application/json\r\n", "%u", mask);
            }
            else if (!mg_strcmp(hm->method, mg_str("POST")))
            {
                /* mg_json_get() returns a token OFFSET (int), not mg_str.
                 * Negative return = error (MG_JSON_NOT_FOUND etc.).
                 * A string token includes the surrounding quotes, so strip them. */
                int           goff  = 0;
                int           glen  = 0;
                struct mg_str group = mg_str_n("", 0);
                long          index = mg_json_get_long(hm->body, "$.index", -1);
                bool          on    = false;

                goff = mg_json_get(hm->body, "$.group", &glen);
                if (goff >= 0 && glen >= 2 && hm->body.buf != NULL && (size_t) goff + (size_t) glen <= hm->body.len &&
                    hm->body.buf[goff] == '"')
                {
                    group = mg_str_n(hm->body.buf + goff + 1, (size_t) glen - 2);
                }

                mg_json_get_bool(hm->body, "$.on", &on);

                if (group.len == 0 || index < 0 || index > 4)
                {
                    mg_http_reply(c,
                                  400,
                                  "Content-Type: application/json\r\n",
                                  "{%m:%m}",
                                  MG_ESC("error"),
                                  MG_ESC("bad request"));
                }
                else if (!mg_strcmp(group, mg_str("relay")))
                {
                    io_relay_write((size_t) index, on);
                    mg_http_reply(c, 200, "Content-Type: application/json\r\n", "{%m:%s}", MG_ESC("ok"), "true");
                }
                else if (!mg_strcmp(group, mg_str("do")))
                {
                    io_out_write((size_t) index, on);
                    mg_http_reply(c, 200, "Content-Type: application/json\r\n", "{%m:%s}", MG_ESC("ok"), "true");
                }
                else
                {
                    mg_http_reply(c,
                                  400,
                                  "Content-Type: application/json\r\n",
                                  "{%m:%m}",
                                  MG_ESC("error"),
                                  MG_ESC("unknown group"));
                }
            }
            else
            {
                mg_http_reply(c,
                              405,
                              "Content-Type: application/json\r\n",
                              "{%m:%m}",
                              MG_ESC("error"),
                              MG_ESC("method not allowed"));
            }
        }
        else
        {
            struct mg_http_serve_opts opts = {0};
            opts.root_dir                  = "/dist";
            opts.fs                        = &mg_fs_packed;
            mg_mem_files                   = mg_packed_files;

            mg_http_serve_dir(c, ev_data, &opts);
        }
    }
}
