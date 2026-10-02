#include "usb_cdc_net.h"
#include "cli.h"
#include "../../frontend/http_handler.h"

static void usb_cdc_app_cli(char* args, void* context)
{
    static Net* net = NULL;
    if (args == NULL)
    {
        printf("usb_cdc_app command received. Usage:\r\n");
        printf("  usb_cdc_app start - Start USB CDC network interface\r\n");
        printf("  usb_cdc_app stop  - Stop USB CDC network interface\r\n");
    }
    else if (strstr(args, "start") == args)
    {
        if (net)
        {
            printf("USB CDC network interface is already running\r\n");
            return;
        }
        net = usb_cdc_net_start(NULL);
        net_start_http(net, "http://0.0.0.0", http_fn, NULL);

        printf("usb_cdc_app command received with args: %s\r\n", args);
    }
    else if (strstr(args, "stop") == args)
    {
        if (net == NULL)
        {
            printf("USB CDC network interface is not running\r\n");
            return;
        }
        usb_cdc_net_stop(net);
        net = NULL;
        printf("USB CDC network interface stopped\r\n");
    }
}

void cdc_net_hello_rhs_start_up(void)
{
    Net* net = usb_cdc_net_start(NULL);
    net_start_http(net, "http://0.0.0.0", http_fn, NULL);
}
