#include <libgen.h>
#include <limits.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "cli.h"
#include "config.h"
#include "daemonize.h"
#include "http_server.h"
#include "iface_scan.h"
#include "ipc_server.h"
#include "modbus_io.h"
#include "state.h"
#include "testbench_client.h"
#include "testbench_proto.h"

/* Number of consecutive failed poll cycles before the daemon closes and reopens the
 * serial connection, to recover from a dropped/replugged serial device. */
#define TB_RECONNECT_AFTER_ERRORS 5

/* How often to re-run the IOKit iface presence scan -- physical USB topology only
 * changes on cable replug, so this is decoupled from poll_interval_ms (which can be
 * much faster) instead of rescanning every poll cycle or every HTTP request. */
#define TB_IFACE_REFRESH_MS 2000

static volatile sig_atomic_t g_stop = 0;
static void                  on_signal(int sig)
{
    (void) sig;
    g_stop = 1;
}

/* realpath() requires the target to already exist, which a pidfile/log file usually
 * doesn't yet -- just prefix the cwd manually instead. `buf` must be PATH_MAX. */
static const char* make_absolute(char* buf, size_t cap, const char* path)
{
    if (!path || path[0] == '/')
        return path;
    if (getcwd(buf, cap) == NULL)
        return path;
    size_t n = strlen(buf);
    snprintf(buf + n, cap - n, "/%s", path);
    return buf;
}

/* mg_http_serve_dir() has a surprising quirk: for the "/" URI it unconditionally
 * treats the request as hitting a directory (never calls stat() on root_dir itself),
 * so a root_dir that doesn't actually exist silently serves an empty "Index of /"
 * listing instead of failing loudly. The default --web-root ("web") is relative to
 * the CWD, which only happens to contain a "web/" directory when launched from
 * testbench/io_hub/ -- the far more common `cd build && ./testbench` leaves CWD at
 * testbench/io_hub/build/, which has no "web/" of its own (it lives one level up).
 *
 * So: only when --web-root was left at its default, if cwd-relative "web" doesn't
 * resolve, fall back to resolving it relative to the executable's own location
 * (argv0) instead -- "<exe_dir>/../web" covers both common invocations. */
static const char* resolve_web_root(const char* argv0, const char* web_root, bool is_default, char* buf, size_t cap)
{
    if (realpath(web_root, buf) != NULL)
        return buf;
    if (!is_default)
        return web_root; /* explicit --web-root that doesn't exist: let it fail loudly downstream */

    if (strchr(argv0, '/') != NULL)
    {
        char tmp[PATH_MAX];
        const char* exe_in = argv0[0] == '/' ? argv0 : make_absolute(tmp, sizeof(tmp), argv0);
        char        exe_abs[PATH_MAX];
        if (exe_in && realpath(exe_in, exe_abs) != NULL)
        {
            char dirbuf[PATH_MAX];
            strncpy(dirbuf, exe_abs, sizeof(dirbuf) - 1);
            dirbuf[sizeof(dirbuf) - 1] = '\0';

            char candidate[PATH_MAX];
            snprintf(candidate, sizeof(candidate), "%s/../web", dirname(dirbuf));
            if (realpath(candidate, buf) != NULL)
                return buf;
        }
    }
    return web_root;
}

static void print_usage(const char* argv0)
{
    fprintf(stderr,
            "usage: %s [--config PATH] [--list | --read | --write LABEL=0|1[,...] | --iface | --status]\n"
            "       %s [--config PATH] [--http-addr URL] [--web-root DIR] [--no-http]\n"
            "          [-d|--daemonize] [--pidfile PATH] [--log-file PATH]\n"
            "          (no action flag: run as the polling daemon -- foreground by default,\n"
            "           or detached in the background with -d/--daemonize)\n"
            "\n"
            "--read/--write/--status route through an already-running daemon's IPC socket\n"
            "when one is listening on %s; otherwise --read/--write fall back to a direct,\n"
            "one-shot Modbus session (--status requires a running daemon).\n",
            argv0,
            argv0,
            TB_IPC_DEFAULT_URL);
}

int main(int argc, char** argv)
{
    const char* config_path = "testbench.toml";
    const char* write_arg    = NULL;
    const char* http_addr    = "http://0.0.0.0:8080";
    const char* web_root     = "web";
    const char* pidfile_path = "/tmp/testbench.pid";
    const char* log_file_path = NULL;
    int         do_list = 0, do_read = 0, do_iface = 0, do_status = 0, no_http = 0, daemonize = 0;
    bool        web_root_is_default = true;

    for (int i = 1; i < argc; i++)
    {
        if (strcmp(argv[i], "--config") == 0 && i + 1 < argc)
            config_path = argv[++i];
        else if (strcmp(argv[i], "--list") == 0)
            do_list = 1;
        else if (strcmp(argv[i], "--read") == 0)
            do_read = 1;
        else if (strcmp(argv[i], "--iface") == 0)
            do_iface = 1;
        else if (strcmp(argv[i], "--status") == 0)
            do_status = 1;
        else if (strcmp(argv[i], "--write") == 0 && i + 1 < argc)
            write_arg = argv[++i];
        else if (strcmp(argv[i], "--http-addr") == 0 && i + 1 < argc)
            http_addr = argv[++i];
        else if (strcmp(argv[i], "--web-root") == 0 && i + 1 < argc)
        {
            web_root           = argv[++i];
            web_root_is_default = false;
        }
        else if (strcmp(argv[i], "--no-http") == 0)
            no_http = 1;
        else if (strcmp(argv[i], "-d") == 0 || strcmp(argv[i], "--daemonize") == 0)
            daemonize = 1;
        else if (strcmp(argv[i], "--pidfile") == 0 && i + 1 < argc)
            pidfile_path = argv[++i];
        else if (strcmp(argv[i], "--log-file") == 0 && i + 1 < argc)
            log_file_path = argv[++i];
        else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0)
        {
            print_usage(argv[0]);
            return 0;
        }
        else
        {
            fprintf(stderr, "testbench: unknown argument '%s'\n", argv[i]);
            print_usage(argv[0]);
            return 2;
        }
    }

    TbConfig cfg;
    char     errbuf[256];
    if (tb_config_load(config_path, &cfg, errbuf, sizeof(errbuf)) != 0)
    {
        fprintf(stderr, "testbench: failed to load config '%s': %s\n", config_path, errbuf);
        return 1;
    }

    /* --list/--iface never touch the serial port or the daemon: --list only reads
     * config, --iface only stat()s device paths. */
    if (do_list)
        return tb_cli_list(&cfg);
    if (do_iface)
        return tb_cli_iface(&cfg);

    if (do_read || write_arg || do_status)
    {
        /* If a daemon is already running, route through its IPC socket instead of
         * opening the serial port ourselves -- a one-shot direct session would fight
         * the daemon's poll thread for the same port. */
        TbClient* client = tb_client_connect(NULL);
        if (client && !tb_client_ping(client))
        {
            tb_client_close(client);
            client = NULL;
        }

        int status = 0;

        if (do_status)
        {
            if (!client)
            {
                fprintf(stderr, "testbench: --status requires a running daemon (none found on %s)\n", TB_IPC_DEFAULT_URL);
                status = 1;
            }
            else
            {
                uint64_t uptime_ms, poll_count, poll_errors;
                if (tb_client_get_status(client, &uptime_ms, &poll_count, &poll_errors))
                    printf("uptime=%llums poll_count=%llu poll_errors=%llu\n",
                           (unsigned long long) uptime_ms,
                           (unsigned long long) poll_count,
                           (unsigned long long) poll_errors);
                else
                {
                    fprintf(stderr, "testbench: status query failed\n");
                    status = 1;
                }
            }
        }
        else if (do_read)
        {
            if (client)
            {
                uint32_t bits  = 0;
                uint64_t ts_ms = 0;
                bool     valid = false;
                if (tb_client_get_inputs(client, &bits, &ts_ms, &valid))
                {
                    for (int i = 0; i < cfg.input_label_count; i++)
                    {
                        int idx = cfg.input_labels[i].index;
                        printf("  %-20s : %s\n", cfg.input_labels[i].name, ((bits >> idx) & 1u) ? "ON" : "off");
                    }
                }
                else
                {
                    fprintf(stderr, "testbench: ipc read failed\n");
                    status = 1;
                }
            }
            else
            {
                status = tb_cli_read(&cfg);
            }
        }
        else /* write_arg */
        {
            if (client)
            {
                uint32_t mask = 0, value = 0;
                if (tb_parse_write_assignments(&cfg, write_arg, &mask, &value) != 0)
                {
                    status = 1;
                }
                else if (!tb_client_set_coils_mask(client, mask, value))
                {
                    fprintf(stderr, "testbench: ipc write failed\n");
                    status = 1;
                }
                else
                {
                    for (int bit = 0; bit < 32; bit++)
                        if (mask & (1u << bit))
                        {
                            int         addr = cfg.output_min_addr + bit;
                            const char* name = tb_config_output_label(&cfg, addr);
                            printf("  %-20s -> %s\n", name ? name : "?", (value & (1u << bit)) ? "ON" : "off");
                        }
                }
            }
            else
            {
                status = tb_cli_write(&cfg, write_arg);
            }
        }

        if (client)
            tb_client_close(client);
        return status;
    }

    /* Resolve any relative paths before tb_daemonize()'s chdir("/") -- otherwise they'd
     * resolve against "/" afterwards. web_root in particular needs this even with no
     * explicit flag: its default ("web") is relative. */
    char web_root_abs[PATH_MAX];
    web_root = resolve_web_root(argv[0], web_root, web_root_is_default, web_root_abs, sizeof(web_root_abs));
    char pidfile_abs[PATH_MAX];
    pidfile_path = make_absolute(pidfile_abs, sizeof(pidfile_abs), pidfile_path);
    char log_file_abs[PATH_MAX];
    if (log_file_path)
        log_file_path = make_absolute(log_file_abs, sizeof(log_file_abs), log_file_path);

    if (daemonize)
    {
        if (!log_file_path || log_file_path[0] == '\0')
            log_file_path = "/tmp/testbench.log";
        /* Must happen before any threads exist or FDs (serial port, sockets) are
         * opened -- fork() only carries the calling thread into the child. */
        if (tb_daemonize(log_file_path) != 0)
        {
            fprintf(stderr, "testbench: daemonize failed\n");
            return 1;
        }
        tb_write_pidfile(pidfile_path);
    }

    fprintf(stderr,
            "testbench: usb_location=0x%x baud=%d inputs_id=%d outputs_id=%d input_regs=%d "
            "outputs=[%d..%d] (%d labels) poll=%dms\n",
            cfg.usb_location,
            cfg.baudrate,
            cfg.inputs_id,
            cfg.outputs_id,
            cfg.input_count,
            cfg.output_min_addr,
            cfg.output_min_addr + cfg.output_span - 1,
            cfg.output_label_count,
            cfg.poll_interval_ms);

    TbState st;
    tb_state_init(&st, cfg.output_span);

    char      mberr[256];
    TbModbus* m = tb_modbus_open(&cfg, mberr, sizeof(mberr));
    if (!m)
    {
        fprintf(stderr, "testbench: %s\n", mberr);
        return 1;
    }

    if (tb_modbus_seed_outputs(m, &cfg, &st) != 0)
        fprintf(stderr, "testbench: warning: could not seed output state from hardware, defaulting to all-off\n");

    TbHttp* http = NULL;
    if (!no_http)
    {
        char index_check[PATH_MAX];
        snprintf(index_check, sizeof(index_check), "%s/index.html", web_root);
        if (access(index_check, F_OK) != 0)
            fprintf(stderr,
                    "testbench: warning: no index.html under --web-root '%s' -- the control panel will "
                    "silently show an empty directory listing instead of an error (a mongoose quirk); "
                    "pass --web-root explicitly if this isn't where web/ actually is\n",
                    web_root);

        http = tb_http_start(&cfg, &st, web_root, http_addr);
        if (http)
            fprintf(stderr, "testbench: http: serving %s on %s\n", web_root, http_addr);
        else
            fprintf(stderr, "testbench: http: failed to start (continuing without it)\n");
    }

    TbIpc* ipc = tb_ipc_start(&cfg, &st, NULL);
    if (ipc)
        fprintf(stderr, "testbench: ipc: listening on %s\n", TB_IPC_DEFAULT_URL);
    else
        fprintf(stderr, "testbench: ipc: failed to start (continuing without it)\n");

    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    fprintf(stderr, "testbench: polling (Ctrl+C to stop)\n");
    /* The in-place \r status refresh below only looks right on a real terminal, which
     * actually interprets \r as "return to column 0 of this row" -- piped/captured
     * output (a log file, this daemon launched from a non-interactive wrapper) has no
     * such cursor, so an un-terminated \r line there just sits open for whatever the
     * next write happens to be (even from the stderr stream) to run on right after it. */
    bool     stdout_is_tty = !daemonize && isatty(fileno(stdout));
    int      consecutive_errors = 0;
    uint64_t iface_next_ts      = 0;
    while (!g_stop)
    {
        int rc = tb_modbus_cycle(m, &cfg, &st);

        uint64_t now = tb_now_ms();
        if (now >= iface_next_ts)
        {
            bool present[TB_MAX_IFACES];
            char path[TB_MAX_IFACES][TB_IFACE_PATH_LEN];
            for (int i = 0; i < cfg.iface_count; i++)
                present[i] = tb_iface_detect(&cfg.iface[i], path[i], sizeof(path[i]));

            pthread_mutex_lock(&st.mutex);
            memcpy(st.iface_present, present, sizeof(bool) * (size_t) cfg.iface_count);
            memcpy(st.iface_path, path, sizeof(path[0]) * (size_t) cfg.iface_count);
            st.iface_ts_ms = now;
            pthread_mutex_unlock(&st.mutex);

            iface_next_ts = now + TB_IFACE_REFRESH_MS;
        }

        /* A dropped serial device (e.g. a USB-serial adapter unplugged) fails every
         * cycle forever on the same stale fd -- it never recovers on its own even once
         * the port comes back, so force a close+reopen after a run of failures. */
        if (rc != 0)
        {
            consecutive_errors++;
            if (consecutive_errors >= TB_RECONNECT_AFTER_ERRORS)
            {
                /* Deliberately printed to stdout, the same stream as the status line
                 * below, not stderr: two separate streams give no ordering guarantee
                 * once something downstream (a terminal multiplexer, a log relay, this
                 * command's own output capture) reads both -- bytes from each can be
                 * interleaved out of the order this process actually wrote them in,
                 * which is what caused these messages to visually run into/swap places
                 * with the status line. One stream keeps them in true write order.
                 * Leading "\n" (tty only): the status line below has no trailing
                 * newline there (it overwrites itself in place), so without this these
                 * messages would run on right after it instead of starting fresh. */
                fprintf(stdout,
                        "%stestbench: %d consecutive poll errors, reconnecting (usb_location=0x%x)...\n",
                        stdout_is_tty ? "\n" : "",
                        consecutive_errors,
                        cfg.usb_location);
                if (tb_modbus_reconnect(m, &cfg, mberr, sizeof(mberr)) == 0)
                    fprintf(stdout, "testbench: reconnected (usb_location=0x%x)\n", cfg.usb_location);
                else
                    fprintf(stdout, "testbench: reconnect failed: %s\n", mberr);
                fflush(stdout);
                consecutive_errors = 0;
            }
        }
        else
        {
            consecutive_errors = 0;
        }

        if (!daemonize)
        {
            /* Copy out just the fields the status line needs, then print without
             * holding the mutex -- fprintf/fflush can block indefinitely on a stalled
             * stdout consumer (scroll-locked terminal, slow pipe reader), and every
             * IPC/HTTP request needing st.mutex would stall right along with it. */
            uint32_t input_bits;
            uint64_t poll_count, poll_errors;
            pthread_mutex_lock(&st.mutex);
            input_bits  = st.input_bits;
            poll_count  = st.poll_count;
            poll_errors = st.poll_errors;
            pthread_mutex_unlock(&st.mutex);

            fprintf(stdout,
                    "%sinputs=0x%08x outputs=%d..%d polls=%llu errors=%llu %-5s%s",
                    stdout_is_tty ? "\r" : "",
                    input_bits,
                    cfg.output_min_addr,
                    cfg.output_min_addr + cfg.output_span - 1,
                    (unsigned long long) poll_count,
                    (unsigned long long) poll_errors,
                    rc == 0 ? "ok" : "ERR",
                    stdout_is_tty ? "" : "\n");
            fflush(stdout);
        }

        usleep((useconds_t) cfg.poll_interval_ms * 1000);
    }

    fprintf(stderr, "\ntestbench: shutting down\n");
    if (ipc)
        tb_ipc_stop(ipc);
    if (http)
        tb_http_stop(http);
    tb_modbus_close(m);
    tb_state_destroy(&st);
    if (daemonize)
        tb_remove_pidfile(pidfile_path);
    return 0;
}
