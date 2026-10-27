#include "testbench_client.h"

#include <nng/nng.h>
#include <nng/protocol/reqrep0/req.h>
#include <stdlib.h>
#include <string.h>

#include "testbench_proto.h"

struct TbClient
{
    nng_socket sock;
};

TbClient* tb_client_connect(const char* url)
{
    if (!url || url[0] == '\0')
        url = TB_IPC_DEFAULT_URL;

    TbClient* c = calloc(1, sizeof(*c));
    if (!c)
        return NULL;

    if (nng_req0_open(&c->sock) != 0)
    {
        free(c);
        return NULL;
    }
    nng_socket_set_ms(c->sock, NNG_OPT_RECVTIMEO, 1000);
    nng_socket_set_ms(c->sock, NNG_OPT_SENDTIMEO, 1000);

    if (nng_dial(c->sock, url, NULL, 0) != 0)
    {
        nng_socket_close(c->sock);
        free(c);
        return NULL;
    }
    return c;
}

void tb_client_close(TbClient* c)
{
    if (!c)
        return;
    nng_socket_close(c->sock);
    free(c);
}

static bool do_call(TbClient* c, uint8_t op, const void* payload, size_t payload_len, void* resp_body, size_t resp_body_len)
{
    uint8_t     req[TB_IPC_MAX_FRAME];
    TbReqHeader h = {TB_PROTO_VERSION, op};
    memcpy(req, &h, sizeof(h));
    size_t req_len = sizeof(h);
    if (payload && payload_len)
    {
        memcpy(req + req_len, payload, payload_len);
        req_len += payload_len;
    }

    if (nng_send(c->sock, req, req_len, 0) != 0)
        return false;

    uint8_t resp[TB_IPC_MAX_FRAME];
    size_t  len = sizeof(resp);
    if (nng_recv(c->sock, resp, &len, 0) != 0)
        return false;
    if (len < sizeof(TbRespHeader))
        return false;

    TbRespHeader rh;
    memcpy(&rh, resp, sizeof(rh));
    if (rh.status != TB_STATUS_OK)
        return false;
    if (resp_body && resp_body_len)
    {
        if (len < sizeof(rh) + resp_body_len)
            return false;
        memcpy(resp_body, resp + sizeof(rh), resp_body_len);
    }
    return true;
}

bool tb_client_ping(TbClient* c)
{
    return do_call(c, TB_OP_PING, NULL, 0, NULL, 0);
}

bool tb_client_get_inputs(TbClient* c, uint32_t* bits, uint64_t* ts_ms, bool* valid)
{
    TbInputsResp body;
    if (!do_call(c, TB_OP_GET_INPUTS, NULL, 0, &body, sizeof(body)))
        return false;
    if (bits)
        *bits = body.bits;
    if (ts_ms)
        *ts_ms = body.ts_ms;
    if (valid)
        *valid = body.valid != 0;
    return true;
}

bool tb_client_get_outputs(TbClient* c, uint32_t* bits, int32_t* min_addr, int32_t* span)
{
    TbOutputsResp body;
    if (!do_call(c, TB_OP_GET_OUTPUTS, NULL, 0, &body, sizeof(body)))
        return false;
    if (bits)
        *bits = body.bits;
    if (min_addr)
        *min_addr = body.min_addr;
    if (span)
        *span = body.span;
    return true;
}

bool tb_client_set_coils_mask(TbClient* c, uint32_t mask, uint32_t value)
{
    TbSetCoilsReq req = {mask, value};
    return do_call(c, TB_OP_SET_COILS_MASK, &req, sizeof(req), NULL, 0);
}

bool tb_client_get_status(TbClient* c, uint64_t* uptime_ms, uint64_t* poll_count, uint64_t* poll_errors)
{
    TbStatusResp body;
    if (!do_call(c, TB_OP_GET_STATUS, NULL, 0, &body, sizeof(body)))
        return false;
    if (uptime_ms)
        *uptime_ms = body.uptime_ms;
    if (poll_count)
        *poll_count = body.poll_count;
    if (poll_errors)
        *poll_errors = body.poll_errors;
    return true;
}

bool tb_client_iface_available(TbClient* c, TbIfaceId iface, char* out_path, size_t out_path_len)
{
    if (out_path && out_path_len)
        out_path[0] = '\0';

    TbIfaceStatusReq  req = {(uint8_t) iface};
    TbIfaceStatusResp body;
    if (!do_call(c, TB_OP_GET_IFACE_STATUS, &req, sizeof(req), &body, sizeof(body)))
        return false; /* daemon unreachable, or iface wasn't one of the TB_IFACE_* values */

    bool available = body.present != 0;
    if (available && out_path && out_path_len)
    {
        size_t n = sizeof(body.path) < out_path_len ? sizeof(body.path) : out_path_len - 1;
        memcpy(out_path, body.path, n);
        out_path[n] = '\0';
    }
    return available;
}
