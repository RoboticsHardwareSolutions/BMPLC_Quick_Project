/* App mode test application for usb_bridge, driven over RTT by the host tests in ../testbench/.
 *
 *   usb_bridge_echo can|rs232|rs485   start the bridge in App mode with the echo callback (restarts if running)
 *   usb_bridge_echo stop              stop it
 *   usb_bridge_echo burst <n>         RS232/RS485: send n counter bytes (i & 0xFF) from the CLI thread (queue path)
 *   usb_bridge_echo state             print the bridge state
 *
 * CAN echo, frames from the host:
 *   data frame id          -> same frame with id + 1 (std ids wrap at 0x7FF, ext ids at 0x1FFFFFFF)
 *   RTR frame id, DLC n    -> data frame id + 1, DLC n, payload 0, 1, .. n-1
 *   std 0x7FF [01 hi lo]   -> burst of (hi << 8 | lo) std frames 0x100, payload = 16-bit big endian sequence number
 *   std 0x7FF [02]         -> start a periodic sender: std frame 0x101 every 10 ms with a 16-bit sequence number,
 *                             sent from the timer thread (queue path)
 *   std 0x7FF [03]         -> stop the periodic sender
 * RS232/RS485 echo: bytes from the host come back unchanged (sent from the callback, direct path).
 */
#include "rhs.h"
#include "cli.h"
#include "usb_bridge.h"

#define TAG "usb_bridge_echo"

#define ECHO_CONTROL_ID 0x7FF
#define ECHO_CMD_BURST 0x01
#define ECHO_CMD_PERIODIC_START 0x02
#define ECHO_CMD_PERIODIC_STOP 0x03
#define ECHO_BURST_ID 0x100
#define ECHO_PERIODIC_ID 0x101
#define ECHO_PERIODIC_MS 10
#define ECHO_BURST_CHUNK 64

typedef struct
{
    UsbBridge* bridge;
    RHSTimer*  timer;
    uint16_t   seq;
} UsbBridgeEcho;

static UsbBridgeEcho echo = {0};

/*********************************** CAN ************************************/

static void echo_periodic(void* context)
{
    UNUSED(context);
    RHSHalCANFrameType frame = {.id = ECHO_PERIODIC_ID, .len = 2, .type = FrameTypeStdID};
    frame.payload[0]         = (uint8_t) (echo.seq >> 8);
    frame.payload[1]         = (uint8_t) echo.seq;
    echo.seq++;
    usb_bridge_can_send(echo.bridge, UsbBridgePortUsb, &frame);
}

static void echo_can_burst(uint16_t count)
{
    RHSHalCANFrameType frame = {.id = ECHO_BURST_ID, .len = 2, .type = FrameTypeStdID};
    for (uint32_t i = 0; i < count; i++)
    {
        frame.payload[0] = (uint8_t) (i >> 8);
        frame.payload[1] = (uint8_t) i;
        usb_bridge_can_send(echo.bridge, UsbBridgePortUsb, &frame);
    }
}

static void echo_on_can(UsbBridgePort from, const RHSHalCANFrameType* frame, void* context)
{
    UNUSED(from);
    UNUSED(context);

    if (frame->type == FrameTypeStdID && frame->id == ECHO_CONTROL_ID && !frame->rtr)
    {
        if (frame->len >= 3 && frame->payload[0] == ECHO_CMD_BURST)
        {
            echo_can_burst((uint16_t) ((frame->payload[1] << 8) | frame->payload[2]));
        }
        else if (frame->len >= 1 && frame->payload[0] == ECHO_CMD_PERIODIC_START)
        {
            echo.seq = 0;
            rhs_timer_start(echo.timer, ECHO_PERIODIC_MS);
        }
        else if (frame->len >= 1 && frame->payload[0] == ECHO_CMD_PERIODIC_STOP)
        {
            rhs_timer_stop(echo.timer);
        }
        return;
    }

    RHSHalCANFrameType reply = *frame;
    reply.id                 = (frame->id + 1) & (frame->type == FrameTypeExtID ? 0x1FFFFFFFU : 0x7FFU);
    if (frame->rtr)
    {
        reply.rtr = false;
        for (uint8_t i = 0; i < reply.len; i++)
        {
            reply.payload[i] = i;
        }
    }
    usb_bridge_can_send(echo.bridge, UsbBridgePortUsb, &reply);
}

/*********************************** SERIAL ************************************/

static void echo_on_data(UsbBridgePort from, const uint8_t* data, size_t len, void* context)
{
    UNUSED(from);
    UNUSED(context);
    usb_bridge_data_send(echo.bridge, UsbBridgePortUsb, data, len);
}

static void echo_data_burst(uint32_t count)
{
    uint8_t  chunk[ECHO_BURST_CHUNK];
    uint32_t sent = 0;
    while (sent < count)
    {
        uint32_t len = count - sent < sizeof(chunk) ? count - sent : sizeof(chunk);
        for (uint32_t i = 0; i < len; i++)
        {
            chunk[i] = (uint8_t) (sent + i);
        }
        // Queue path: wait while the bridge queue is full
        while (!usb_bridge_data_send(echo.bridge, UsbBridgePortUsb, chunk, len))
        {
            rhs_delay_ms(1);
        }
        sent += len;
    }
}

/*********************************** CLI ************************************/

static void echo_stop(void)
{
    if (echo.bridge != NULL)
    {
        rhs_timer_stop(echo.timer);
        usb_bridge_stop(echo.bridge);
        echo.bridge = NULL;
    }
}

static void echo_start(UsbBridgeTarget target)
{
    echo_stop();
    UsbBridgeConfig cfg = {
        .target   = target,
        .mode     = UsbBridgeModeApp,
        .baudrate = target == UsbBridgeTargetCan ? 500000 : 9600,
    };
    const char* reason = usb_bridge_check(&cfg);
    if (reason != NULL)
    {
        printf("error: %s app: %s\r\n", usb_bridge_target_name(target), reason);
        return;
    }
    echo.bridge = usb_bridge_start(&cfg);
    if (echo.bridge == NULL)
    {
        printf("error: not started\r\n");
        return;
    }
    if (target == UsbBridgeTargetCan)
    {
        usb_bridge_set_can_callback(echo.bridge, echo_on_can, NULL);
    }
    else
    {
        usb_bridge_set_data_callback(echo.bridge, echo_on_data, NULL);
    }
    printf("started %s\r\n", usb_bridge_target_name(target));
}

static void echo_state(void)
{
    if (echo.bridge == NULL)
    {
        printf("stopped\r\n");
        return;
    }
    UsbBridgeState st;
    usb_bridge_get_state(echo.bridge, &st);
    printf("open: %d, baudrate: %lu, usb rx: %lu, tx: %lu, tx drops: %lu, app rx: %lu, tx: %lu\r\n",
           st.open,
           (unsigned long) st.baudrate,
           (unsigned long) st.usb_rx,
           (unsigned long) st.usb_tx,
           (unsigned long) st.usb_tx_drops,
           (unsigned long) st.app_rx,
           (unsigned long) st.app_tx);
}

static void echo_cli(char* args, void* context)
{
    UNUSED(context);
    if (args == NULL)
    {
        printf("usb_bridge_echo can|rs232|rs485|stop|state|burst <n>\r\n");
    }
    else if (strcmp(args, "can") == 0)
    {
        echo_start(UsbBridgeTargetCan);
    }
    else if (strcmp(args, "rs232") == 0)
    {
        echo_start(UsbBridgeTargetRs232);
    }
    else if (strcmp(args, "rs485") == 0)
    {
        echo_start(UsbBridgeTargetRs485);
    }
    else if (strcmp(args, "stop") == 0)
    {
        echo_stop();
        printf("stopped\r\n");
    }
    else if (strcmp(args, "state") == 0)
    {
        echo_state();
    }
    else if (strncmp(args, "burst ", 6) == 0 && echo.bridge != NULL)
    {
        UsbBridgeConfig cfg;
        usb_bridge_get_config(echo.bridge, &cfg);
        if (cfg.target == UsbBridgeTargetCan)
        {
            printf("error: burst is for rs232/rs485\r\n");
            return;
        }
        uint32_t count = (uint32_t) atoi(&args[6]);
        echo_data_burst(count);
        printf("sent %lu\r\n", (unsigned long) count);
    }
    else
    {
        printf("error: unknown command\r\n");
    }
}

void usb_bridge_echo_start_up(void)
{
    echo.timer = rhs_timer_alloc(echo_periodic, RHSTimerTypePeriodic, NULL);

    Cli* cli = rhs_record_open(RECORD_CLI);
    cli_add_command(cli, "usb_bridge_echo", echo_cli, NULL);
    rhs_record_close(RECORD_CLI);
}
