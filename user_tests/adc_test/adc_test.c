#include <stdlib.h>
#include "rhs.h"
#include "rhs_hal.h"
#include "cli.h"
#include "runit.h"
#include "stm32g0xx_ll_bus.h"

#define TAG "adc_test"

/* Only internal channels: they need no pin, so the test fits any G0B1 board */

/* Datasheet limits: VDDA is 3.0..3.6 V, VREFINT is 1.212 V typ */
#define TEST_VDDA_MIN_MV     (3000)
#define TEST_VDDA_MAX_MV     (3600)
#define TEST_VREFINT_MIN_RAW (1212 * 4095 / TEST_VDDA_MAX_MV - 50)
#define TEST_VREFINT_MAX_RAW (1212 * 4095 / TEST_VDDA_MIN_MV + 50)
/* The board works indoors, the die is a bit warmer than the air */
#define TEST_TEMP_MIN_C (10)
#define TEST_TEMP_MAX_C (70)
/* On the 32 pin package VBAT is bonded to VDD inside, VBAT/3 divider adds its error */
#define TEST_VBAT_DELTA_MV (150)
/* Oversampled reads of a steady signal */
#define TEST_REPEAT_DELTA_RAW (8)
/* Different clock / oversampling of the same signal */
#define TEST_CONFIG_DELTA_RAW (20)

static void test_vdda(RHSHalAdcHandle* adc)
{
    uint16_t vrefint = rhs_hal_adc_read(adc, RHSHalAdcChannelVREFINT);
    runit_ge(vrefint, TEST_VREFINT_MIN_RAW);
    runit_le(vrefint, TEST_VREFINT_MAX_RAW);

    int32_t vdda = (int32_t) rhs_hal_adc_convert_vref(adc, vrefint);
    runit_ge(vdda, TEST_VDDA_MIN_MV);
    runit_le(vdda, TEST_VDDA_MAX_MV);

    // Full scale is the VDDA measured by configure
    int32_t full_scale = (int32_t) rhs_hal_adc_convert_to_voltage(adc, 4095);
    runit_le(abs(full_scale - vdda), 10);
    printf("vrefint=%u vdda=%ld mV full_scale=%ld mV\r\n", vrefint, (long) vdda, (long) full_scale);
}

static void test_temp(RHSHalAdcHandle* adc)
{
    uint16_t raw  = rhs_hal_adc_read(adc, RHSHalAdcChannelTEMPSENSOR);
    int32_t  temp = (int32_t) rhs_hal_adc_convert_temp(adc, raw);
    runit_ge(temp, TEST_TEMP_MIN_C);
    runit_le(temp, TEST_TEMP_MAX_C);
    printf("temp raw=%u t=%ld C\r\n", raw, (long) temp);
}

static void test_vbat(RHSHalAdcHandle* adc)
{
    int32_t  vdda = (int32_t) rhs_hal_adc_convert_to_voltage(adc, 4095);
    uint16_t raw  = rhs_hal_adc_read(adc, RHSHalAdcChannelVBAT);
    int32_t  vbat = (int32_t) rhs_hal_adc_convert_vbat(adc, raw);
    runit_le(abs(vbat - vdda), TEST_VBAT_DELTA_MV);
    printf("vbat raw=%u vbat=%ld mV\r\n", raw, (long) vbat);
}

/* Channel switching: VREFINT read after other channels is not affected by them */
static void test_channel_switch(RHSHalAdcHandle* adc)
{
    uint16_t before = rhs_hal_adc_read(adc, RHSHalAdcChannelVREFINT);
    (void) rhs_hal_adc_read(adc, RHSHalAdcChannelVBAT);
    (void) rhs_hal_adc_read(adc, RHSHalAdcChannelTEMPSENSOR);
    uint16_t after = rhs_hal_adc_read(adc, RHSHalAdcChannelVREFINT);
    runit_le(abs((int) before - (int) after), TEST_REPEAT_DELTA_RAW);
}

/* Every clock and oversampling gives the same value of a steady signal */
static void test_configure_ex(RHSHalAdcHandle* adc)
{
    rhs_hal_adc_configure(adc);
    int reference = rhs_hal_adc_read(adc, RHSHalAdcChannelVREFINT);

    const RHSHalAdcClock      clocks[]      = {RHSHalAdcClockSync16, RHSHalAdcClockSync32};
    const RHSHalAdcOversample oversamples[] = {RHSHalAdcOversampleNone, RHSHalAdcOversample2, RHSHalAdcOversample256};
    for (size_t c = 0; c < COUNT_OF(clocks); c++)
    {
        for (size_t o = 0; o < COUNT_OF(oversamples); o++)
        {
            rhs_hal_adc_configure_ex(adc, clocks[c], oversamples[o], RHSHalAdcSamplingtime39_5);
            int first  = rhs_hal_adc_read(adc, RHSHalAdcChannelVREFINT);
            int second = rhs_hal_adc_read(adc, RHSHalAdcChannelVREFINT);
            runit_le(abs(first - reference), TEST_CONFIG_DELTA_RAW);
            runit_le(abs(first - second),
                     oversamples[o] == RHSHalAdcOversampleNone ? TEST_CONFIG_DELTA_RAW : TEST_REPEAT_DELTA_RAW);
        }
    }
}

/* ADC works again after release, with its clock and regulator turned off */
static void test_reacquire(void)
{
    for (int i = 0; i < 3; i++)
    {
        RHSHalAdcHandle* adc = rhs_hal_adc_acquire();
        rhs_hal_adc_configure(adc);
        int32_t vdda = (int32_t) rhs_hal_adc_convert_to_voltage(adc, 4095);
        runit_ge(vdda, TEST_VDDA_MIN_MV);
        runit_le(vdda, TEST_VDDA_MAX_MV);
        rhs_hal_adc_release(adc);
        runit_false(LL_APB2_GRP1_IsEnabledClock(LL_APB2_GRP1_PERIPH_ADC));
    }
}

static void adc_test_command(char* args, void* context)
{
    UNUSED(args);
    UNUSED(context);

    runit_counter_assert_passes   = 0;
    runit_counter_assert_failures = 0;

    RHS_LOG_I(TAG, "started");

    RHSHalAdcHandle* adc = rhs_hal_adc_acquire();
    rhs_hal_adc_configure(adc);
    test_vdda(adc);
    test_temp(adc);
    test_vbat(adc);
    test_channel_switch(adc);
    test_configure_ex(adc);
    rhs_hal_adc_release(adc);

    test_reacquire();

    runit_report();
}

void adc_test(void)
{
    Cli* cli = rhs_record_open(RECORD_CLI);
    cli_add_command(cli, "adc_test", adc_test_command, NULL);
    rhs_record_close(RECORD_CLI);
}
