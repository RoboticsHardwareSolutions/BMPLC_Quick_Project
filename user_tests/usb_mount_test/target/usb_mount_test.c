/* Tests of the USB mount callback (thirdparty/rhs/hal/rhs_hal_usb/rhs_hal_usb.c), driven over RTT by the host tests
 * in ../testbench/.
 *
 *   usb_mount_test    unit tests: the TinyUSB device callbacks are called by hand. Only while no USB interface runs:
 *                     the real state is unmounted then and the test leaves it unmounted.
 *   usb_mount         one line: `mounted: 0|1 mount: <n> umount: <n>`, events seen since start-up / reset
 *   usb_mount reset   zero the event counters
 */
#include <string.h>
#include "rhs.h"
#include "rhs_hal.h"
#include "cli.h"
#include "runit.h"

#define TAG "usb_mount_test"

typedef struct
{
    uint32_t mount;
    uint32_t umount;
    bool     last;
} MountEvents;

static void mount_record(bool mounted, void* context)
{
    MountEvents* events = context;
    RHS_CRITICAL_ENTER();
    if (mounted)
    {
        events->mount++;
    }
    else
    {
        events->umount++;
    }
    events->last = mounted;
    RHS_CRITICAL_EXIT();
}

/*********************************** UNIT TESTS ************************************/

static MountEvents a;
static MountEvents b;

static void events_reset(void)
{
    memset(&a, 0, sizeof(a));
    memset(&b, 0, sizeof(b));
}

static void test_mount_umount(void)
{
    events_reset();
    runit_false(rhs_hal_usb_is_mounted());

    tud_mount_cb();
    runit_true(rhs_hal_usb_is_mounted());
    runit_eq(a.mount, 1);
    runit_true(a.last);

    // Repeated events are not reported again
    tud_mount_cb();
    runit_eq(a.mount, 1);

    tud_umount_cb();
    runit_false(rhs_hal_usb_is_mounted());
    runit_eq(a.umount, 1);
    runit_false(a.last);

    tud_umount_cb();
    runit_eq(a.umount, 1);
}

static void test_suspend_resume(void)
{
    events_reset();

    tud_mount_cb();
    runit_eq(a.mount, 1);

    // Pulled cable without VBUS sensing: suspend
    tud_suspend_cb(false);
    runit_false(rhs_hal_usb_is_mounted());
    runit_eq(a.umount, 1);

    tud_suspend_cb(true);
    runit_eq(a.umount, 1);

    tud_resume_cb();
    runit_true(rhs_hal_usb_is_mounted());
    runit_eq(a.mount, 2);

    // Mount after a suspend: the cable is back and the host enumerated again
    tud_suspend_cb(false);
    tud_mount_cb();
    runit_true(rhs_hal_usb_is_mounted());
    runit_eq(a.umount, 2);
    runit_eq(a.mount, 3);

    tud_umount_cb();
    runit_eq(a.umount, 3);
}

static void test_resume_unconfigured(void)
{
    events_reset();

    // Bus activity without a configuration from the host is not a mount
    tud_suspend_cb(false);
    tud_resume_cb();
    runit_false(rhs_hal_usb_is_mounted());
    runit_eq(a.mount, 0);
    runit_eq(a.umount, 0);

    // Umount while suspended: reported once, the next resume does not mount
    tud_mount_cb();
    tud_suspend_cb(false);
    tud_umount_cb();
    tud_resume_cb();
    runit_false(rhs_hal_usb_is_mounted());
    runit_eq(a.mount, 1);
    runit_eq(a.umount, 1);
}

static void test_two_subscribers(void)
{
    events_reset();
    runit_true(rhs_hal_usb_add_mount_callback(mount_record, &b));

    tud_mount_cb();
    runit_eq(a.mount, 1);
    runit_eq(b.mount, 1);

    // Removed: no more events, the other one still gets them
    rhs_hal_usb_remove_mount_callback(mount_record, &b);
    tud_umount_cb();
    runit_eq(a.umount, 1);
    runit_eq(b.umount, 0);

    // Removing a pair which is not set changes nothing
    rhs_hal_usb_remove_mount_callback(mount_record, &b);
    tud_mount_cb();
    tud_umount_cb();
    runit_eq(a.mount, 2);
    runit_eq(b.mount, 1);
}

static void test_capacity(void)
{
    static MountEvents extra[RHS_HAL_USB_MOUNT_CALLBACKS_MAX];
    size_t             added = 0;

    events_reset();
    memset(extra, 0, sizeof(extra));
    // The slots taken by other subscribers (the `usb_mount` counter, the application) are not known here
    while (added < RHS_HAL_USB_MOUNT_CALLBACKS_MAX && rhs_hal_usb_add_mount_callback(mount_record, &extra[added]))
    {
        added++;
    }
    bool full = !rhs_hal_usb_add_mount_callback(mount_record, &b);

    tud_mount_cb();
    tud_umount_cb();
    for (size_t i = 0; i < added; i++)
    {
        rhs_hal_usb_remove_mount_callback(mount_record, &extra[i]);
    }

    runit_true(full);
    runit_eq(b.mount, 0);
    for (size_t i = 0; i < added; i++)
    {
        runit_eq(extra[i].mount, 1);
        runit_eq(extra[i].umount, 1);
    }
    // A freed slot is taken again
    runit_true(rhs_hal_usb_add_mount_callback(mount_record, &b));
    rhs_hal_usb_remove_mount_callback(mount_record, &b);
}

static void usb_mount_test(char* args, void* context)
{
    UNUSED(args);
    UNUSED(context);

    runit_counter_assert_passes   = 0;
    runit_counter_assert_failures = 0;

    if (rhs_hal_usb_get_interface() != NULL)
    {
        printf("usb_mount_test: skipped, a USB interface runs (usb stop first)\r\n");
        runit_report();
        return;
    }

    runit_true(rhs_hal_usb_add_mount_callback(mount_record, &a));
    test_mount_umount();
    test_suspend_resume();
    test_resume_unconfigured();
    test_two_subscribers();
    test_capacity();
    rhs_hal_usb_remove_mount_callback(mount_record, &a);

    // Leave the real state: no interface, unmounted
    tud_umount_cb();
    runit_report();
}

void rhs_usb_mount_test(void)
{
    Cli* cli = rhs_record_open(RECORD_CLI);
    cli_add_command(cli, "usb_mount_test", usb_mount_test, NULL);
    rhs_record_close(RECORD_CLI);
}

/*********************************** HOST TESTS ************************************/

static MountEvents counter;

static void usb_mount_cli(char* args, void* context)
{
    UNUSED(context);
    if (args != NULL && strcmp(args, "reset") == 0)
    {
        RHS_CRITICAL_ENTER();
        counter.mount  = 0;
        counter.umount = 0;
        RHS_CRITICAL_EXIT();
        printf("reset\r\n");
    }
    else if (args == NULL)
    {
        printf("mounted: %d mount: %lu umount: %lu\r\n",
               rhs_hal_usb_is_mounted() ? 1 : 0,
               (unsigned long) counter.mount,
               (unsigned long) counter.umount);
    }
    else
    {
        printf("usb_mount [reset]\r\n");
    }
}

void usb_mount_start_up(void)
{
    rhs_assert(rhs_hal_usb_add_mount_callback(mount_record, &counter));

    Cli* cli = rhs_record_open(RECORD_CLI);
    cli_add_command(cli, "usb_mount", usb_mount_cli, NULL);
    rhs_record_close(RECORD_CLI);
}
