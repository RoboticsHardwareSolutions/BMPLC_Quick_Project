#include "rhs.h"
#include "rhs_hal.h"
#include "cli.h"

/**
 * @file exti_test.c
 * @brief EXTI edge-count service with CLI commands for IN0-IN4
 *
 * Reconfigures all five inputs into EXTI rise+fall interrupt mode (via
 * io_in_exti_enable) and counts every edge per channel. The bench -- not the
 * device -- judges pass/fail: user_tests/exti_test/testbench/exti_test.py
 * toggles each PLC_<T>_IN<n> coil and checks that exactly one edge lands on
 * channel n (and zero on the others), which proves the EXTI source routing,
 * the NVIC vector enable and the line mask are all correct for that pin.
 * io_test already covers the polled level (IN*_IS_HIGH); this module covers
 * the hardware interrupt path itself.
 *
 * Available CLI commands:
 * - exti: EXTI edge-count command
 *   Usage:
 *     exti            - Show edge counts for IN0-IN4
 *     exti reset      - Reset all counters to zero
 *     exti ?          - Show help
 */

#define IN_COUNT 5

/* One counter per input channel, bumped from ISR context on every edge
 * (rising AND falling -- the pins are configured RHSGpioModeInterruptRiseFall). */
static volatile uint32_t exti_count[IN_COUNT];

static void exti_isr_callback(void* context)
{
    volatile uint32_t* count = (volatile uint32_t*)context;
    (*count)++;
}

static void exti_test(char* args, void* context)
{
    (void)context;

    if (args != NULL && strcmp(args, "reset") == 0)
    {
        for (uint8_t i = 0; i < IN_COUNT; i++)
            exti_count[i] = 0;
        printf("EXTI counters reset\n");
        return;
    }

    if (args != NULL && (strcmp(args, "?") == 0 || strcmp(args, "help") == 0))
    {
        printf("EXTI Commands:\n");
        printf("Usage:\n");
        printf("  exti            - Show edge counts for IN0-IN4\n");
        printf("  exti reset      - Reset all counters to zero\n");
        printf("  exti ?          - Show this help\n");
        return;
    }

    if (args == NULL)
    {
        printf("EXTI counts:\n");
        for (uint8_t i = 0; i < IN_COUNT; i++)
            printf("  IN%d: %lu\n", i, (unsigned long)exti_count[i]);
        return;
    }

    printf("Invalid argument: %s\n", args);
    printf("Type 'exti ?' for help\n");
}

void rhs_exti_test(void)
{
    // Reconfigure IN0-4 from io_init()'s plain polling mode into EXTI rise+fall
    // interrupt sources; counters accumulate from this point on. Runs from the
    // loader service, i.e. after rhs_hal_init()/io_init() and with the CLI up.
    for (uint8_t ch = 0; ch < IN_COUNT; ch++)
        io_in_exti_enable(ch, exti_isr_callback, &exti_count[ch]);

    Cli* cli = rhs_record_open(RECORD_CLI);
    cli_add_command(cli, "exti", exti_test, NULL);
    rhs_record_close(RECORD_CLI);
}
