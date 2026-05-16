#include "usb_cdc_net.h"

static void http_fn(struct mg_connection* c, int ev, void* ev_data)
{
    if (ev == MG_EV_HTTP_MSG)
    {
        struct mg_http_serve_opts opts = {0};
        opts.root_dir = "/dist";
        opts.fs       = &mg_fs_packed;
        mg_http_serve_dir(c, ev_data, &opts);
    }
}

void cdc_net_hello_rhs_start_up(void)
{
    Net* net = usb_cdc_net_start(NULL);
    net_start_http(net, "http://0.0.0.0", http_fn, NULL);
}
