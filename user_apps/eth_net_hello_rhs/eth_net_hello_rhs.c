#include "eth_net.h"
#include "cli.h"

static void http_fn(struct mg_connection* c, int ev, void* ev_data)
{
    if (ev == MG_EV_HTTP_MSG)
    {
        struct mg_http_serve_opts opts = {0};
        opts.root_dir                  = "/dist";
        opts.fs                        = &mg_fs_packed;
        mg_http_serve_dir(c, ev_data, &opts);
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
