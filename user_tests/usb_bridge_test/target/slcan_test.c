/* Unit tests of the SLCAN parser/formatter (thirdparty/rhs/applications/services/usb_bridge/slcan.c).
 * On target: CLI command `slcan_test`. The test cases do not use RHS, so the file also builds on the host with
 * -DSLCAN_TEST_HOST (main() below) together with slcan.c and runit. */
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "runit.h"
#include "slcan.h"

static SlcanCmd parse(const char* line)
{
    SlcanCmd cmd;
    memset(&cmd, 0xA5, sizeof(cmd));
    slcan_parse(line, strlen(line), &cmd);
    return cmd;
}

static void test_simple_commands(void)
{
    runit_eq(parse("").type, SlcanCmdNone);
    runit_eq(parse("O").type, SlcanCmdOpen);
    runit_eq(parse("L").type, SlcanCmdListenOnly);
    runit_eq(parse("C").type, SlcanCmdClose);
    runit_eq(parse("F").type, SlcanCmdStatus);
    runit_eq(parse("V").type, SlcanCmdVersion);
    runit_eq(parse("v").type, SlcanCmdSwVersion);
    runit_eq(parse("N").type, SlcanCmdSerial);
    runit_eq(parse("M00000000").type, SlcanCmdAcceptFilter);
    runit_eq(parse("mFFFFFFFF").type, SlcanCmdAcceptFilter);

    // Trailing garbage and unknown commands
    runit_eq(parse("OX").type, SlcanCmdInvalid);
    runit_eq(parse("X").type, SlcanCmdInvalid);
    runit_eq(parse("M0000000").type, SlcanCmdInvalid);
    runit_eq(parse("M0000000G").type, SlcanCmdInvalid);
}

static void test_bitrate(void)
{
    static const uint32_t expected[] = {10000, 20000, 50000, 100000, 125000, 250000, 500000, 800000, 1000000};
    char                  line[3]    = "S0";

    for (uint8_t i = 0; i < 9; i++)
    {
        line[1]      = (char) ('0' + i);
        SlcanCmd cmd = parse(line);
        runit_eq(cmd.type, SlcanCmdSetBitrate);
        runit_eq(cmd.bitrate, expected[i]);
    }
    runit_eq(parse("S9").type, SlcanCmdInvalid);
    runit_eq(parse("S").type, SlcanCmdInvalid);
    runit_eq(parse("S66").type, SlcanCmdInvalid);
    runit_eq(slcan_bitrate_from_index(9), 0);
}

static void test_timestamp(void)
{
    SlcanCmd cmd = parse("Z0");
    runit_eq(cmd.type, SlcanCmdTimestamp);
    runit_false(cmd.timestamp);
    cmd = parse("Z1");
    runit_eq(cmd.type, SlcanCmdTimestamp);
    runit_true(cmd.timestamp);
    runit_eq(parse("Z2").type, SlcanCmdInvalid);
}

static void test_parse_std_frame(void)
{
    SlcanCmd cmd = parse("t1233112233");
    runit_eq(cmd.type, SlcanCmdTransmit);
    runit_eq(cmd.frame.id, 0x123);
    runit_eq(cmd.frame.type, FrameTypeStdID);
    runit_false(cmd.frame.rtr);
    runit_eq(cmd.frame.len, 3);
    runit_eq(cmd.frame.payload[0], 0x11);
    runit_eq(cmd.frame.payload[1], 0x22);
    runit_eq(cmd.frame.payload[2], 0x33);
    runit_eq(cmd.frame.payload[3], 0);

    // Lower case hex, DLC 0 and 8
    cmd = parse("t7ff0");
    runit_eq(cmd.type, SlcanCmdTransmit);
    runit_eq(cmd.frame.id, 0x7FF);
    runit_eq(cmd.frame.len, 0);
    cmd = parse("t0008deadbeefcafebabe");
    runit_eq(cmd.type, SlcanCmdTransmit);
    runit_eq(cmd.frame.id, 0);
    runit_eq(cmd.frame.len, 8);
    runit_eq(cmd.frame.payload[0], 0xDE);
    runit_eq(cmd.frame.payload[7], 0xBE);
}

static void test_parse_ext_and_rtr(void)
{
    SlcanCmd cmd = parse("T1FFFFFFF2ABCD");
    runit_eq(cmd.type, SlcanCmdTransmit);
    runit_eq(cmd.frame.id, 0x1FFFFFFF);
    runit_eq(cmd.frame.type, FrameTypeExtID);
    runit_eq(cmd.frame.len, 2);
    runit_eq(cmd.frame.payload[0], 0xAB);
    runit_eq(cmd.frame.payload[1], 0xCD);

    cmd = parse("r1234");
    runit_eq(cmd.type, SlcanCmdTransmit);
    runit_true(cmd.frame.rtr);
    runit_eq(cmd.frame.type, FrameTypeStdID);
    runit_eq(cmd.frame.id, 0x123);
    runit_eq(cmd.frame.len, 4);

    cmd = parse("R000000018");
    runit_eq(cmd.type, SlcanCmdTransmit);
    runit_true(cmd.frame.rtr);
    runit_eq(cmd.frame.type, FrameTypeExtID);
    runit_eq(cmd.frame.id, 1);
    runit_eq(cmd.frame.len, 8);
}

static void test_parse_invalid_frames(void)
{
    runit_eq(parse("t800").type, SlcanCmdInvalid);              // std id > 0x7FF
    runit_eq(parse("T200000000").type, SlcanCmdInvalid);        // ext id > 0x1FFFFFFF
    runit_eq(parse("t1239").type, SlcanCmdInvalid);             // DLC > 8
    runit_eq(parse("t1232112233").type, SlcanCmdInvalid);       // more data than DLC
    runit_eq(parse("t123211").type, SlcanCmdInvalid);           // less data than DLC
    runit_eq(parse("t1231G0").type, SlcanCmdInvalid);           // not hex data
    runit_eq(parse("t12").type, SlcanCmdInvalid);               // too short
    runit_eq(parse("tX230").type, SlcanCmdInvalid);             // not hex id
    runit_eq(parse("r12300").type, SlcanCmdInvalid);            // RTR with data
    runit_eq(parse("T1234567").type, SlcanCmdInvalid);          // ext id too short
}

static void test_format(void)
{
    char               out[SLCAN_FRAME_MAX];
    RHSHalCANFrameType frame = {.id = 0x123, .len = 3, .type = FrameTypeStdID, .payload = {0x11, 0x22, 0x33}};

    size_t len = slcan_format_frame(&frame, out);
    runit_eq(len, strlen("t1233112233\r"));
    runit_memeq(out, "t1233112233\r", len);

    frame = (RHSHalCANFrameType) {.id = 0x1ABCDEF0, .len = 8, .type = FrameTypeExtID, .payload = {0, 1, 2, 3, 4, 5, 6, 0xFF}};
    len   = slcan_format_frame(&frame, out);
    runit_eq(len, SLCAN_FRAME_MAX);
    runit_memeq(out, "T1ABCDEF0800010203040506FF\r", len);

    frame = (RHSHalCANFrameType) {.id = 0x7FF, .len = 5, .type = FrameTypeStdID, .rtr = true};
    len   = slcan_format_frame(&frame, out);
    runit_memeq(out, "r7FF5\r", len);

    frame = (RHSHalCANFrameType) {.id = 0x42, .len = 0, .type = FrameTypeExtID, .rtr = true};
    len   = slcan_format_frame(&frame, out);
    runit_memeq(out, "R000000420\r", len);

    // Not representable
    frame = (RHSHalCANFrameType) {.id = 0x800, .len = 0, .type = FrameTypeStdID};
    runit_eq(slcan_format_frame(&frame, out), 0);
    frame = (RHSHalCANFrameType) {.id = 0x1, .len = 9, .type = FrameTypeStdID};
    runit_eq(slcan_format_frame(&frame, out), 0);
    frame = (RHSHalCANFrameType) {.id = 0x1, .len = 1, .type = FrameTypeNO};
    runit_eq(slcan_format_frame(&frame, out), 0);
}

static void test_roundtrip(void)
{
    char               out[SLCAN_FRAME_MAX];
    RHSHalCANFrameType frame = {.id = 0x0ABCDEF, .len = 6, .type = FrameTypeExtID, .payload = {9, 8, 7, 6, 5, 4}};

    size_t   len = slcan_format_frame(&frame, out);
    SlcanCmd cmd;
    slcan_parse(out, len - 1, &cmd);  // without CR
    runit_eq(cmd.type, SlcanCmdTransmit);
    runit_eq(cmd.frame.id, frame.id);
    runit_eq(cmd.frame.type, frame.type);
    runit_eq(cmd.frame.len, frame.len);
    runit_memeq(cmd.frame.payload, frame.payload, frame.len);
}

static void test_reader(void)
{
    SlcanReader reader;
    SlcanCmd    cmd;
    int         lines = 0;
    const char* input = "C\rS6\r\nO\rt1230\r";

    slcan_reader_reset(&reader);
    SlcanCmdType expected[] = {SlcanCmdClose, SlcanCmdSetBitrate, SlcanCmdOpen, SlcanCmdTransmit};
    for (const char* p = input; *p; p++)
    {
        if (slcan_reader_push(&reader, *p, &cmd))
        {
            runit_lt(lines, 4);
            runit_eq(cmd.type, expected[lines]);
            lines++;
        }
    }
    runit_eq(lines, 4);

    // Line longer than SLCAN_LINE_MAX: invalid, the next line parses again
    for (int i = 0; i < SLCAN_LINE_MAX + 5; i++)
    {
        runit_false(slcan_reader_push(&reader, '1', &cmd));
    }
    runit_true(slcan_reader_push(&reader, '\r', &cmd));
    runit_eq(cmd.type, SlcanCmdInvalid);
    runit_false(slcan_reader_push(&reader, 'O', &cmd));
    runit_true(slcan_reader_push(&reader, '\r', &cmd));
    runit_eq(cmd.type, SlcanCmdOpen);

    // Empty line (bare CR)
    runit_true(slcan_reader_push(&reader, '\r', &cmd));
    runit_eq(cmd.type, SlcanCmdNone);
}

static void slcan_test_run(void)
{
    runit_counter_assert_passes   = 0;
    runit_counter_assert_failures = 0;

    test_simple_commands();
    test_bitrate();
    test_timestamp();
    test_parse_std_frame();
    test_parse_ext_and_rtr();
    test_parse_invalid_frames();
    test_format();
    test_roundtrip();
    test_reader();

    runit_report();
}

#if defined(SLCAN_TEST_HOST)

int main(void)
{
    slcan_test_run();
    return runit_counter_assert_failures == 0 ? 0 : 1;
}

#else

#    include "rhs.h"
#    include "cli.h"

static void slcan_test(char* args, void* context)
{
    UNUSED(args);
    UNUSED(context);
    slcan_test_run();
}

void rhs_slcan_test(void)
{
    Cli* cli = rhs_record_open(RECORD_CLI);
    cli_add_command(cli, "slcan_test", slcan_test, NULL);
    rhs_record_close(RECORD_CLI);
}

#endif
