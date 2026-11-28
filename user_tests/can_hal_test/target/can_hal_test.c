#include <stdlib.h>
#include <string.h>
#include "rhs.h"
#include "rhs_hal.h"
#include "rhs_hal_can.h"
#include "cli.h"

/**
 * @file can_hal_test.c
 * @brief CLI harness exercising rhs_hal_can (CAN1) directly, for BMPLC_M and BMPLC_XL
 *
 * Unlike usb_bridge_test's slcan_test (parser-only, host-buildable), this talks to the real
 * CAN1 peripheral through rhs_hal_can -- no SLCAN, no usb_bridge. The bench judges pass/fail
 * via its own CAN adapter wired to the board's CAN bus: user_tests/can_hal_test/testbench/.
 *
 * @warning On BMPLC_M (STM32F103xE), bxCAN and USB share the same dedicated 512-byte SRAM
 * (RM0008) -- real CAN bus traffic while USB CDC NET is up (the board's normal boot
 * configuration) can corrupt that shared memory and hang the whole MCU, not just CAN. This is
 * the same constraint usb_bridge_can.c's can_unsupported() already rejects for non-App modes
 * on this board. The testbench therefore only exercises real tx/rx traffic on BMPLC_XL; see
 * user_tests/can_hal_test/testbench/test_can_hal.py.
 *
 * Available CLI commands:
 *   can_hal init <baud>                        - rhs_hal_can_init(CAN1, baud) + start rx/sce callbacks
 *   can_hal deinit                             - rhs_hal_can_deinit(CAN1)
 *   can_hal tx <id_hex> <ext:0|1> <rtr:0|1> [hex bytes, no spaces]
 *                                                 id is range-checked against the 11-bit standard /
 *                                                 29-bit extended max for the given `ext`; ext/rtr must be
 *                                                 exactly "0" or "1"; data is 0-16 hex chars (0-8 bytes).
 *   can_hal txburst <count> <id_hex> <ext> <rtr> [len] - send N frames (len 0-8, zeroed
 *                                                 payload, default 0) in one call, no RTT
 *                                                 round trip between them (see can_hal_cmd_txburst)
 *   can_hal rx                                 - pop one received frame, or "none"
 *   can_hal stat                               - print RHSHalCANStatistic plus this module's own
 *                                                 sce/busoff event counts and rx_queue soft-drop count
 *   can_hal ?                                  - help
 */

#define CAN_HAL_TEST_CHANNEL RHSHalCANId1
#define CAN_HAL_TEST_RX_QUEUE_LEN 32
#define CAN_STD_ID_MAX 0x7FFu       /* 11-bit standard identifier */
#define CAN_EXT_ID_MAX 0x1FFFFFFFu  /* 29-bit extended identifier */

typedef struct
{
    bool             running;
    RHSMessageQueue* rx_queue; /**< RHSHalCANFrameType, filled from can_hal_test_rx_isr() */
    uint32_t         sce_events;
    uint32_t         busoff_events;  /**< subset of sce_events where RHSHalCANSCEEventBusOff was set */
    uint32_t         rx_queue_drops; /**< frames the HAL delivered but rx_queue (CAN_HAL_TEST_RX_QUEUE_LEN
                                        deep) was full for -- distinct from RHSHalCANStatistic.rx_ovfs,
                                        which only counts the hardware FIFO overflowing */
} CanHalTest;

static CanHalTest can_hal_test;

static void can_hal_test_rx_isr(RHSHalCANId id, void* context)
{
    CanHalTest*        test = (CanHalTest*) context;
    RHSHalCANFrameType frame;

    if (!rhs_hal_can_rx(id, &frame))
    {
        return;
    }
    if (rhs_message_queue_put(test->rx_queue, &frame, 0) != RHSStatusOk)
    {
        test->rx_queue_drops++;
    }
}

static void can_hal_test_sce_isr(RHSHalCANId id, RHSHalCANSCEEvent event, void* context)
{
    UNUSED(id);
    CanHalTest* test = (CanHalTest*) context;
    if (event != 0)
    {
        test->sce_events++;
    }
    if (event & RHSHalCANSCEEventBusOff)
    {
        test->busoff_events++;
    }
}

static bool parse_hex_nibble(char c, uint8_t* out)
{
    if (c >= '0' && c <= '9')
    {
        *out = (uint8_t) (c - '0');
    }
    else if (c >= 'a' && c <= 'f')
    {
        *out = (uint8_t) (c - 'a' + 10);
    }
    else if (c >= 'A' && c <= 'F')
    {
        *out = (uint8_t) (c - 'A' + 10);
    }
    else
    {
        return false;
    }
    return true;
}

/* Exactly 2 hex digits: strtol() would happily keep consuming the next byte's digits too,
 * since they are valid hex characters -- there is no delimiter between bytes. */
static bool parse_hex_byte(const char* s, uint8_t* out)
{
    uint8_t hi, lo;
    if (!parse_hex_nibble(s[0], &hi) || !parse_hex_nibble(s[1], &lo))
    {
        return false;
    }
    *out = (uint8_t) ((hi << 4) | lo);
    return true;
}

static void can_hal_cmd_init(char* arg)
{
    if (arg == NULL)
    {
        printf("usage: can_hal init <baud>\r\n");
        return;
    }
    char*         end  = NULL;
    unsigned long baud = strtoul(arg, &end, 10);
    if (end == arg || baud == 0)
    {
        printf("bad baud: %s\r\n", arg);
        return;
    }

    if (can_hal_test.running)
    {
        // Allow re-init without a separate 'deinit' first: rhs_hal_can_init() would otherwise
        // assert on the already-enabled channel.
        rhs_hal_can_deinit(CAN_HAL_TEST_CHANNEL);
        can_hal_test.running = false;
    }

    if (!rhs_hal_can_init(CAN_HAL_TEST_CHANNEL, (uint32_t) baud))
    {
        printf("init failed\r\n");
        return;
    }
    rhs_message_queue_reset(can_hal_test.rx_queue);
    can_hal_test.sce_events     = 0;
    can_hal_test.busoff_events  = 0;
    can_hal_test.rx_queue_drops = 0;
    rhs_hal_can_async_rx_start(CAN_HAL_TEST_CHANNEL, can_hal_test_rx_isr, &can_hal_test);
    rhs_hal_can_async_sce(CAN_HAL_TEST_CHANNEL, can_hal_test_sce_isr, &can_hal_test);
    // No rhs_hal_can_tx_cmplt_cb() registration needed: tx_msgs is now counted synchronously
    // inside rhs_hal_can_tx() itself.
    can_hal_test.running = true;
    printf("started\r\n");
}

static void can_hal_cmd_deinit(void)
{
    if (!can_hal_test.running)
    {
        printf("not running\r\n");
        return;
    }
    rhs_hal_can_deinit(CAN_HAL_TEST_CHANNEL);
    can_hal_test.running = false;
    printf("stopped\r\n");
}

/* Accepts exactly "0" or "1" -- anything else (empty, garbage, "2", "01") is rejected rather
 * than silently treated as false like a bare `str[0] == '1'` check would. */
static bool parse_bit_flag(const char* s, bool* out)
{
    if (s == NULL || s[0] == '\0' || s[1] != '\0' || (s[0] != '0' && s[0] != '1'))
    {
        return false;
    }
    *out = (s[0] == '1');
    return true;
}

/* Parses+validates the <id_hex> <ext:0|1> <rtr:0|1> prefix shared by `tx` and `txburst`.
 * Prints the matching error and returns false on any failure. */
static bool parse_frame_header(const char* id_str, const char* ext_str, const char* rtr_str, uint32_t* id_out,
                                bool* ext_out, bool* rtr_out)
{
    char*         end = NULL;
    unsigned long id  = strtoul(id_str, &end, 16);
    if (end == id_str || *end != '\0')
    {
        printf("bad id: %s\r\n", id_str);
        return false;
    }

    if (!parse_bit_flag(ext_str, ext_out))
    {
        printf("bad args: ext must be 0 or 1, got %s\r\n", ext_str);
        return false;
    }
    if (!parse_bit_flag(rtr_str, rtr_out))
    {
        printf("bad args: rtr must be 0 or 1, got %s\r\n", rtr_str);
        return false;
    }

    uint32_t id_max = *ext_out ? CAN_EXT_ID_MAX : CAN_STD_ID_MAX;
    if (id > id_max)
    {
        printf("bad id: 0x%lx exceeds the %s-ID max of 0x%lx\r\n",
               id,
               *ext_out ? "extended" : "standard",
               (unsigned long) id_max);
        return false;
    }

    *id_out = (uint32_t) id;
    return true;
}

static void can_hal_cmd_tx(char* args)
{
    if (!can_hal_test.running)
    {
        printf("not running\r\n");
        return;
    }
    if (args == NULL)
    {
        printf("usage: can_hal tx <id_hex> <ext:0|1> <rtr:0|1> [hex bytes]\r\n");
        return;
    }

    char* id_str   = strtok(args, " ");
    char* ext_str  = strtok(NULL, " ");
    char* rtr_str  = strtok(NULL, " ");
    char* data_str = strtok(NULL, " ");

    if (id_str == NULL || ext_str == NULL || rtr_str == NULL)
    {
        printf("usage: can_hal tx <id_hex> <ext:0|1> <rtr:0|1> [hex bytes]\r\n");
        return;
    }

    uint32_t id;
    bool     ext, rtr;
    if (!parse_frame_header(id_str, ext_str, rtr_str, &id, &ext, &rtr))
    {
        return;
    }

    size_t data_len = data_str ? strlen(data_str) : 0;
    if (data_len % 2 != 0 || data_len / 2 > 8)
    {
        printf("bad data: %s\r\n", data_str);
        return;
    }

    RHSHalCANFrameType frame = {0};
    frame.id                 = id;
    frame.type                = ext ? FrameTypeExtID : FrameTypeStdID;
    frame.rtr                 = rtr;
    frame.len                 = (uint8_t) (data_len / 2);
    for (uint8_t i = 0; i < frame.len; i++)
    {
        if (!parse_hex_byte(data_str + i * 2, &frame.payload[i]))
        {
            printf("bad data: %s\r\n", data_str);
            return;
        }
    }

    printf(rhs_hal_can_tx(CAN_HAL_TEST_CHANNEL, &frame) ? "tx ok\r\n" : "tx failed\r\n");
}

/* Sends `count` identical empty frames back to back in one CLI call, with no RTT round trip
 * in between -- unlike one `tx` per command, this survives an unacked frame's retry/error
 * storm starting the instant the first frame is loaded: that storm's interrupt rate can leave
 * the CLI task too starved to ever get back to parsing a *second* RTT command, even one
 * already sitting in the input buffer. Built to drive bxCAN's 3 TX mailboxes to overflow
 * (RHSHalCANStatistic.tx_ovfs) deterministically -- see test_tx_mailbox_overflow_and_busoff_recovery. */
static void can_hal_cmd_txburst(char* args)
{
    if (!can_hal_test.running)
    {
        printf("not running\r\n");
        return;
    }
    if (args == NULL)
    {
        printf("usage: can_hal txburst <count> <id_hex> <ext:0|1> <rtr:0|1> [len 0-8]\r\n");
        return;
    }

    char* count_str = strtok(args, " ");
    char* id_str    = strtok(NULL, " ");
    char* ext_str   = strtok(NULL, " ");
    char* rtr_str   = strtok(NULL, " ");
    char* len_str   = strtok(NULL, " ");  // optional; defaults to 0 (an empty frame)

    if (count_str == NULL || id_str == NULL || ext_str == NULL || rtr_str == NULL)
    {
        printf("usage: can_hal txburst <count> <id_hex> <ext:0|1> <rtr:0|1> [len 0-8]\r\n");
        return;
    }

    char*         end   = NULL;
    unsigned long count = strtoul(count_str, &end, 10);
    if (end == count_str || *end != '\0' || count == 0)
    {
        printf("bad count: %s\r\n", count_str);
        return;
    }

    unsigned long len = 0;
    if (len_str != NULL)
    {
        end = NULL;
        len = strtoul(len_str, &end, 10);
        if (end == len_str || *end != '\0' || len > 8)
        {
            printf("bad len: %s\r\n", len_str);
            return;
        }
    }

    uint32_t id;
    bool     ext, rtr;
    if (!parse_frame_header(id_str, ext_str, rtr_str, &id, &ext, &rtr))
    {
        return;
    }

    RHSHalCANFrameType frame = {0};
    frame.id                 = id;
    frame.type                = ext ? FrameTypeExtID : FrameTypeStdID;
    frame.rtr                 = rtr;
    frame.len                 = (uint8_t) len;  // payload stays zeroed; only the DLC matters here

    uint32_t ok = 0, failed = 0;
    for (unsigned long i = 0; i < count; i++)
    {
        if (rhs_hal_can_tx(CAN_HAL_TEST_CHANNEL, &frame))
        {
            ok++;
        }
        else
        {
            failed++;
        }
    }
    // Reported inline rather than left for a follow-up `can_hal stat`: once a mailbox is stuck
    // retrying an unacked frame, the resulting SCE interrupt storm can make a *second* RTT
    // round trip take a very long time to get a readable response at all.
    printf("ok=%lu failed=%lu tx_ovfs=%lu\r\n",
           (unsigned long) ok,
           (unsigned long) failed,
           (unsigned long) rhs_hal_can_get_statistic(CAN_HAL_TEST_CHANNEL).tx_ovfs);
}

static void can_hal_cmd_rx(void)
{
    if (!can_hal_test.running)
    {
        printf("not running\r\n");
        return;
    }

    RHSHalCANFrameType frame;
    if (rhs_message_queue_get(can_hal_test.rx_queue, &frame, 0) != RHSStatusOk)
    {
        printf("none\r\n");
        return;
    }

    printf("id=%lx ext=%d rtr=%d len=%u data=",
           (unsigned long) frame.id,
           frame.type == FrameTypeExtID ? 1 : 0,
           frame.rtr ? 1 : 0,
           frame.len);
    for (uint8_t i = 0; i < frame.len; i++)
    {
        printf("%02x", frame.payload[i]);
    }
    printf("\r\n");
}

static void can_hal_cmd_stat(void)
{
    RHSHalCANStatistic stat = rhs_hal_can_get_statistic(CAN_HAL_TEST_CHANNEL);
    printf("tx_msgs=%lu tx_errs=%lu tx_ovfs=%lu rx_msgs=%lu rx_errs=%lu rx_ovfs=%lu sce=%lu busoff=%lu "
           "rx_drops=%lu\r\n",
           (unsigned long) stat.tx_msgs,
           (unsigned long) stat.tx_errs,
           (unsigned long) stat.tx_ovfs,
           (unsigned long) stat.rx_msgs,
           (unsigned long) stat.rx_errs,
           (unsigned long) stat.rx_ovfs,
           (unsigned long) can_hal_test.sce_events,
           (unsigned long) can_hal_test.busoff_events,
           (unsigned long) can_hal_test.rx_queue_drops);
}

static void can_hal_cmd_help(void)
{
    printf("CAN HAL test commands:\r\n");
    printf("  can_hal init <baud>                                  - start CAN1\r\n");
    printf("  can_hal deinit                                       - stop CAN1\r\n");
    printf("  can_hal tx <id_hex> <ext:0|1> <rtr:0|1> [hex bytes]   - send one frame (id/ext/rtr validated)\r\n");
    printf("  can_hal txburst <count> <id_hex> <ext> <rtr> [len]   - send N frames back to back\r\n");
    printf("  can_hal rx                                           - pop one received frame, or 'none'\r\n");
    printf("  can_hal stat                                         - print statistics\r\n");
    printf("  can_hal ?                                            - this help\r\n");
}

static void can_hal_test_command(char* args, void* context)
{
    UNUSED(context);

    if (args == NULL || strcmp(args, "?") == 0 || strcmp(args, "help") == 0)
    {
        can_hal_cmd_help();
        return;
    }

    char* space = strchr(args, ' ');
    char* rest  = NULL;
    if (space != NULL)
    {
        *space = '\0';
        rest   = space + 1;
    }
    char* cmd = args;

    if (strcmp(cmd, "init") == 0)
    {
        can_hal_cmd_init(rest);
    }
    else if (strcmp(cmd, "deinit") == 0)
    {
        can_hal_cmd_deinit();
    }
    else if (strcmp(cmd, "tx") == 0)
    {
        can_hal_cmd_tx(rest);
    }
    else if (strcmp(cmd, "txburst") == 0)
    {
        can_hal_cmd_txburst(rest);
    }
    else if (strcmp(cmd, "rx") == 0)
    {
        can_hal_cmd_rx();
    }
    else if (strcmp(cmd, "stat") == 0)
    {
        can_hal_cmd_stat();
    }
    else
    {
        printf("Unknown subcommand: %s\r\n", cmd);
        can_hal_cmd_help();
    }
}

void rhs_can_hal_test(void)
{
    can_hal_test.rx_queue = rhs_message_queue_alloc(CAN_HAL_TEST_RX_QUEUE_LEN, sizeof(RHSHalCANFrameType));

    Cli* cli = rhs_record_open(RECORD_CLI);
    cli_add_command(cli, "can_hal", can_hal_test_command, NULL);
    rhs_record_close(RECORD_CLI);
}
