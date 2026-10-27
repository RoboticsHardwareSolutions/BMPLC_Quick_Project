#include "ipc_server.h"

#include <nng/nng.h>
#include <nng/protocol/reqrep0/rep.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "testbench_proto.h"

struct TbIpc
{
    nng_socket      sock;
    pthread_t       thread;
    volatile int    stop;
    const TbConfig* cfg;
    TbState*        st;
};

static size_t handle_request(TbIpc* ipc, const uint8_t* req, size_t req_len, uint8_t* resp)
{
    TbRespHeader rh  = {TB_PROTO_VERSION, TB_STATUS_ERROR};
    size_t       off = sizeof(rh);

    if (req_len < sizeof(TbReqHeader))
    {
        memcpy(resp, &rh, sizeof(rh));
        return sizeof(rh);
    }
    TbReqHeader reqh;
    memcpy(&reqh, req, sizeof(reqh));
    const uint8_t* payload     = req + sizeof(TbReqHeader);
    size_t         payload_len = req_len - sizeof(TbReqHeader);

    switch (reqh.op)
    {
        case TB_OP_PING:
        {
            rh.status = TB_STATUS_OK;
            memcpy(resp, &rh, sizeof(rh));
            return sizeof(rh);
        }
        case TB_OP_GET_INPUTS:
        {
            TbInputsResp body;
            pthread_mutex_lock(&ipc->st->mutex);
            body.bits  = ipc->st->input_bits;
            body.ts_ms = ipc->st->input_ts_ms;
            body.valid = ipc->st->input_valid ? 1 : 0;
            pthread_mutex_unlock(&ipc->st->mutex);

            /* The Modbus input poll isn't currently producing valid data (bus error,
             * device unplugged, etc) -- report the call itself as failed rather than
             * hand back a snapshot that's silently stale. */
            if (!body.valid)
                break;

            rh.status = TB_STATUS_OK;
            memcpy(resp, &rh, sizeof(rh));
            memcpy(resp + off, &body, sizeof(body));
            return off + sizeof(body);
        }
        case TB_OP_GET_OUTPUTS:
        {
            bool          output_valid;
            TbOutputsResp body = {0};
            pthread_mutex_lock(&ipc->st->mutex);
            output_valid = ipc->st->output_valid;
            for (int i = 0; i < ipc->cfg->output_span && i < 32; i++)
                if (ipc->st->output_bits[i])
                    body.bits |= (1u << i);
            pthread_mutex_unlock(&ipc->st->mutex);
            body.min_addr = ipc->cfg->output_min_addr;
            body.span     = ipc->cfg->output_span;

            /* Same reasoning as TB_OP_GET_INPUTS -- the last coil write didn't actually
             * reach the bus, so the in-memory desired state isn't a trustworthy snapshot
             * of hardware reality right now. */
            if (!output_valid)
                break;

            rh.status = TB_STATUS_OK;
            memcpy(resp, &rh, sizeof(rh));
            memcpy(resp + off, &body, sizeof(body));
            return off + sizeof(body);
        }
        case TB_OP_SET_COILS_MASK:
        {
            if (payload_len < sizeof(TbSetCoilsReq))
                break;
            TbSetCoilsReq in;
            memcpy(&in, payload, sizeof(in));

            pthread_mutex_lock(&ipc->st->mutex);
            bool output_valid = ipc->st->output_valid;
            if (output_valid)
                for (int i = 0; i < ipc->cfg->output_span && i < 32; i++)
                    if (in.mask & (1u << i))
                        ipc->st->output_bits[i] = (uint8_t) ((in.value >> i) & 1u);
            pthread_mutex_unlock(&ipc->st->mutex);

            /* Reject outright rather than silently queue the write -- a caller told
             * "false" should be able to trust that nothing happened. */
            if (!output_valid)
                break;

            rh.status = TB_STATUS_OK;
            memcpy(resp, &rh, sizeof(rh));
            return off;
        }
        case TB_OP_GET_STATUS:
        {
            TbStatusResp body;
            pthread_mutex_lock(&ipc->st->mutex);
            body.uptime_ms    = tb_now_ms() - ipc->st->start_ts_ms;
            body.poll_count  = ipc->st->poll_count;
            body.poll_errors = ipc->st->poll_errors;
            pthread_mutex_unlock(&ipc->st->mutex);

            rh.status = TB_STATUS_OK;
            memcpy(resp, &rh, sizeof(rh));
            memcpy(resp + off, &body, sizeof(body));
            return off + sizeof(body);
        }
        default:
            break;
    }

    memcpy(resp, &rh, sizeof(rh)); /* status is already TB_STATUS_ERROR */
    return sizeof(rh);
}

static void* ipc_thread(void* arg)
{
    TbIpc* ipc = (TbIpc*) arg;
    while (!ipc->stop)
    {
        uint8_t req[TB_IPC_MAX_FRAME];
        size_t  len = sizeof(req);
        int     rc  = nng_recv(ipc->sock, req, &len, 0);
        if (rc != 0)
            continue; /* recv-timeout elapsed (normal, lets us re-check ipc->stop) or error */

        uint8_t resp[TB_IPC_MAX_FRAME];
        size_t  resp_len = handle_request(ipc, req, len, resp);
        nng_send(ipc->sock, resp, resp_len, 0);
    }
    return NULL;
}

TbIpc* tb_ipc_start(const TbConfig* cfg, TbState* st, const char* url)
{
    if (!url || url[0] == '\0')
        url = TB_IPC_DEFAULT_URL;

    TbIpc* ipc = calloc(1, sizeof(*ipc));
    if (!ipc)
        return NULL;
    ipc->cfg = cfg;
    ipc->st  = st;

    int rc = nng_rep0_open(&ipc->sock);
    if (rc != 0)
    {
        fprintf(stderr, "testbench: ipc: nng_rep0_open failed: %s\n", nng_strerror(rc));
        free(ipc);
        return NULL;
    }
    /* Bounded recv so the thread wakes up periodically to check ipc->stop. */
    nng_socket_set_ms(ipc->sock, NNG_OPT_RECVTIMEO, 200);

    rc = nng_listen(ipc->sock, url, NULL, 0);
    if (rc != 0)
    {
        fprintf(stderr, "testbench: ipc: nng_listen(%s) failed: %s\n", url, nng_strerror(rc));
        nng_socket_close(ipc->sock);
        free(ipc);
        return NULL;
    }

    if (pthread_create(&ipc->thread, NULL, ipc_thread, ipc) != 0)
    {
        nng_socket_close(ipc->sock);
        free(ipc);
        return NULL;
    }
    return ipc;
}

void tb_ipc_stop(TbIpc* ipc)
{
    if (!ipc)
        return;
    ipc->stop = 1;
    pthread_join(ipc->thread, NULL);
    nng_socket_close(ipc->sock);
    free(ipc);
}
