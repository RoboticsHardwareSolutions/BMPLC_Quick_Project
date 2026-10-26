#include "http_server.h"

#include <limits.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mongoose.h"

/* Worst-case body size for build_state_json(): TB_MAX_LABELS (48) input + 48 output
 * labels, each up to a 31-char name (TbLabel.name is char[32]) rendered as
 * `"<31 chars>":false,` (~40 bytes), plus TB_MAX_IFACES (8) iface entries up to a
 * 15-char name (~24 bytes), plus the fixed-shape status object and JSON punctuation
 * (~300 bytes): (48+48)*40 + 8*24 + 300 ~= 4332 bytes. Rounded up with headroom. */
#define TB_STATE_JSON_CAP 8192

struct TbHttp
{
    pthread_t       thread;
    volatile int    stop;
    struct mg_mgr   mgr;
    const TbConfig* cfg;
    TbState*        st;
    char            web_root[512];
    char            listen_url[128];
};

static void append_json_str_bool_map(char* out, size_t cap, size_t* off, const char* key, bool value, bool first)
{
    *off += (size_t) snprintf(out + *off, *off < cap ? cap - *off : 0, "%s\"%s\":%s", first ? "" : ",", key, value ? "true" : "false");
}

static void build_state_json(const TbConfig* cfg, TbState* st, char* out, size_t cap)
{
    pthread_mutex_lock(&st->mutex);
    uint32_t in_bits  = st->input_bits;
    bool     in_valid = st->input_valid;
    uint64_t in_ts    = st->input_ts_ms;
    uint8_t  out_bits[TB_MAX_OUTPUT_SPAN];
    memcpy(out_bits, st->output_bits, (size_t) cfg->output_span);
    bool iface_present[TB_MAX_IFACES];
    memcpy(iface_present, st->iface_present, sizeof(bool) * (size_t) cfg->iface_count);
    uint64_t polls = st->poll_count, errs = st->poll_errors, start = st->start_ts_ms;
    pthread_mutex_unlock(&st->mutex);

    size_t off = 0;
    off += (size_t) snprintf(out + off, off < cap ? cap - off : 0, "{\"inputs\":{");
    for (int i = 0; i < cfg->input_label_count; i++)
    {
        int bit = (int) ((in_bits >> cfg->input_labels[i].index) & 1u);
        append_json_str_bool_map(out, cap, &off, cfg->input_labels[i].name, bit != 0, i == 0);
    }
    off += (size_t) snprintf(out + off, off < cap ? cap - off : 0, "},\"outputs\":{");
    for (int i = 0; i < cfg->output_label_count; i++)
    {
        int addr = cfg->output_labels[i].index;
        int bit  = 0;
        if (addr >= cfg->output_min_addr && addr < cfg->output_min_addr + cfg->output_span)
            bit = out_bits[addr - cfg->output_min_addr];
        append_json_str_bool_map(out, cap, &off, cfg->output_labels[i].name, bit != 0, i == 0);
    }
    off += (size_t) snprintf(out + off, off < cap ? cap - off : 0, "},\"iface\":{");
    for (int i = 0; i < cfg->iface_count; i++)
        append_json_str_bool_map(out, cap, &off, cfg->iface[i].name, iface_present[i], i == 0);
    uint64_t now = tb_now_ms();
    off += (size_t) snprintf(out + off,
                              off < cap ? cap - off : 0,
                              "},\"status\":{\"input_valid\":%s,\"input_age_ms\":%llu,"
                              "\"poll_count\":%llu,\"poll_errors\":%llu,\"uptime_ms\":%llu}}",
                              in_valid ? "true" : "false",
                              (unsigned long long) (in_valid ? now - in_ts : 0),
                              (unsigned long long) polls,
                              (unsigned long long) errs,
                              (unsigned long long) (now - start));

    if (off >= cap)
        fprintf(stderr,
                "testbench: http: /api/state JSON truncated (%zu bytes needed, %zu available) -- "
                "too many labels/ifaces configured for TB_STATE_JSON_CAP\n",
                off,
                cap);
}

static void handle_post_outputs(TbHttp* http, struct mg_http_message* hm, struct mg_connection* c)
{
    const TbConfig* cfg = http->cfg;
    TbState*        st  = http->st;

    pthread_mutex_lock(&st->mutex);
    for (int i = 0; i < cfg->output_label_count; i++)
    {
        char path[80];
        snprintf(path, sizeof(path), "$.%s", cfg->output_labels[i].name);
        bool v;
        if (mg_json_get_bool(hm->body, path, &v))
        {
            int addr = cfg->output_labels[i].index;
            if (addr >= cfg->output_min_addr && addr < cfg->output_min_addr + cfg->output_span)
                st->output_bits[addr - cfg->output_min_addr] = v ? 1 : 0;
        }
    }
    pthread_mutex_unlock(&st->mutex);

    char buf[TB_STATE_JSON_CAP];
    build_state_json(cfg, st, buf, sizeof(buf));
    mg_http_reply(c, 200, "Content-Type: application/json\r\n", "%s", buf);
}

static void ev_handler(struct mg_connection* c, int ev, void* ev_data)
{
    if (ev != MG_EV_HTTP_MSG)
        return;
    TbHttp*                  http = (TbHttp*) c->fn_data;
    struct mg_http_message*  hm   = (struct mg_http_message*) ev_data;

    if (mg_match(hm->uri, mg_str("/api/state"), NULL))
    {
        char buf[TB_STATE_JSON_CAP];
        build_state_json(http->cfg, http->st, buf, sizeof(buf));
        mg_http_reply(c, 200, "Content-Type: application/json\r\n", "%s", buf);
    }
    else if (mg_match(hm->uri, mg_str("/api/outputs"), NULL) && mg_strcmp(hm->method, mg_str("POST")) == 0)
    {
        handle_post_outputs(http, hm, c);
    }
    else
    {
        struct mg_http_serve_opts opts = {0};
        opts.root_dir                   = http->web_root;
        mg_http_serve_dir(c, hm, &opts);
    }
}

static void* poll_thread(void* arg)
{
    TbHttp* http = (TbHttp*) arg;
    while (!http->stop)
        mg_mgr_poll(&http->mgr, 100);
    return NULL;
}

TbHttp* tb_http_start(const TbConfig* cfg, TbState* st, const char* web_root, const char* listen_url)
{
    TbHttp* http = calloc(1, sizeof(*http));
    if (!http)
        return NULL;
    http->cfg = cfg;
    http->st  = st;
    /* mg_http_serve_dir() rejects any resolved path containing ".." (mg_path_is_sane),
     * which a relative root_dir like "../web" would trigger as soon as it's appended
     * to a URI -- canonicalize to an absolute path first. */
    char abs_root[PATH_MAX];
    if (realpath(web_root, abs_root) != NULL)
        strncpy(http->web_root, abs_root, sizeof(http->web_root) - 1);
    else
        strncpy(http->web_root, web_root, sizeof(http->web_root) - 1);
    strncpy(http->listen_url, listen_url, sizeof(http->listen_url) - 1);

    mg_log_set(MG_LL_ERROR); /* mongoose defaults to MG_LL_INFO, which is too chatty for a daemon */
    mg_mgr_init(&http->mgr);
    if (mg_http_listen(&http->mgr, http->listen_url, ev_handler, http) == NULL)
    {
        fprintf(stderr, "testbench: http: failed to listen on %s\n", http->listen_url);
        mg_mgr_free(&http->mgr);
        free(http);
        return NULL;
    }

    if (pthread_create(&http->thread, NULL, poll_thread, http) != 0)
    {
        mg_mgr_free(&http->mgr);
        free(http);
        return NULL;
    }
    return http;
}

void tb_http_stop(TbHttp* http)
{
    if (!http)
        return;
    http->stop = 1;
    pthread_join(http->thread, NULL);
    mg_mgr_free(&http->mgr);
    free(http);
}
