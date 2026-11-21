#include "usb_cdc_net.h"
#include "cli.h"
#include "../../frontend/http_handler.h"

static Net*          net           = NULL;
static RHSThread*    switch_thread = NULL;
static bool          switch_start  = false;
static volatile bool switch_busy   = false;

// Own thread: the net thread (un)registers its CLI command on start and stop, which a CLI handler must not wait for
// (it holds the CLI mutex), and starting needs more stack than the timer thread has
static int32_t usb_cdc_app_switch(void* context)
{
    UNUSED(context);
    if (switch_start)
    {
        if (net)
        {
            printf("USB CDC network interface is already running\r\n");
        }
        else
        {
            net = usb_cdc_net_start(NULL);
            net_start_http(net, "http://0.0.0.0", http_fn, NULL);
            printf("USB CDC network interface started\r\n");
        }
    }
    else
    {
        if (net == NULL)
        {
            printf("USB CDC network interface is not running\r\n");
        }
        else
        {
            usb_cdc_net_stop(net);
            net = NULL;
            printf("USB CDC network interface stopped\r\n");
        }
    }
    switch_busy = false;
    return 0;
}

static void usb_cdc_app_run(bool start)
{
    if (switch_busy)
    {
        printf("USB CDC network interface is busy\r\n");
        return;
    }
    // Not busy: the thread is done with the net, the join only waits for its exit
    rhs_thread_join(switch_thread);
    switch_start = start;
    switch_busy  = true;
    rhs_thread_start(switch_thread);
}

static void usb_cdc_app_cli(char* args, void* context)
{
    UNUSED(context);
    if (args == NULL)
    {
        printf("usb_cdc_app command received. Usage:\r\n");
        printf("  usb_cdc_app start - Start USB CDC network interface\r\n");
        printf("  usb_cdc_app stop  - Stop USB CDC network interface\r\n");
    }
    else if (strstr(args, "start") == args)
    {
        usb_cdc_app_run(true);
    }
    else if (strstr(args, "stop") == args)
    {
        usb_cdc_app_run(false);
    }
}

void cdc_net_hello_rhs_start_up(void)
{
    net = usb_cdc_net_start(NULL);
    net_start_http(net, "http://0.0.0.0", http_fn, NULL);

    switch_thread = rhs_thread_alloc("UsbCdcApp", 4 * 1024, usb_cdc_app_switch, NULL);

    Cli* cli = rhs_record_open(RECORD_CLI);
    cli_add_command(cli, "usb_cdc_app", usb_cdc_app_cli, NULL);
    rhs_record_close(RECORD_CLI);
}
