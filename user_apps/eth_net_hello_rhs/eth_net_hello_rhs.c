#include "eth_net.h"
#include "cli.h"

static void http_fn(struct mg_connection* c, int ev, void* ev_data)
{
    if (ev == MG_EV_HTTP_MSG)
    {
        struct mg_http_message* hm = (struct mg_http_message*) ev_data;
        if (mg_match(hm->uri, mg_str("/api/tasks"), NULL))
        {
            if (!mg_strcmp(hm->method, mg_str("GET")))
            {
                static RHSThreadList* thread_list = NULL;
                if (!thread_list)
                    thread_list = rhs_thread_list_create();

                uint16_t count;

                rhs_thread_enumerate(thread_list);  // 0.9 ms
                count = rhs_thread_list_size(thread_list);

                char   body[1024];
                size_t off = 0;

                for (size_t i = 0; i < count; i++)  // 0.3 ms
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
                                       MG_ESC("stack_min_free"),
                                       item->stack_min_free);
                }

                // rhs_thread_list_destroy(thread_list);
                mg_http_reply(c,
                              200,
                              "Content-Type: application/json\r\n",
                              "{%m:[%s]}",
                              MG_ESC("tasks"),
                              body);  // 0.1 ms
            }
        }  // 1.3 ms
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

static void eth_net_app_cli(char* args, void* context)
{
    static Net* net = NULL;
    if (args == NULL)
    {
        printf("eth_net_app command received. Usage:\r\n");
        printf("  eth_net_app start - Start Ethernet network interface\r\n");
        printf("  eth_net_app stop  - Stop Ethernet network interface\r\n");
    }
    else if (strstr(args, "start") == args)
    {
        if (net)
        {
            printf("Ethernet network interface is already running\r\n");
            return;
        }
        net = eth_net_start(NULL, NULL);
        net_start_http(net, "http://0.0.0.0", http_fn, NULL);

        printf("eth_net_app command received with args: %s\r\n", args);
    }
    else if (strstr(args, "stop") == args)
    {
        if (net == NULL)
        {
            printf("Ethernet network interface is not running\r\n");
            return;
        }
        eth_net_stop(net);
        net = NULL;
        printf("Ethernet network interface stopped\r\n");
    }
}

void eth_net_hello_rhs_start_up(void)
{
    Net* net;
    Cli* cli = rhs_record_open(RECORD_CLI);
    cli_add_command(cli, "eth_net_app", eth_net_app_cli, NULL);
}
