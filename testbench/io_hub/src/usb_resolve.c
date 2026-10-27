#include "usb_resolve.h"

#ifdef __APPLE__

#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/IOKitLib.h>

/* Property names verified against the live registry on this machine via
 * `ioreg -p IOUSB -l` -- not pulled from the IOKit headers' kUSBDevicePropertyLocationID
 * etc. macros, whose expansion is MAC_OS_X_VERSION_MIN_REQUIRED-dependent and can
 * resolve to the wrong string on newer deployment targets. */
#define TB_IOREG_LOCATION_KEY "locationID"
#define TB_IOREG_CALLOUT_KEY "IOCalloutDevice"
#define TB_IOREG_SERIAL_CLASS "IOSerialBSDClient"

/* "locationID" lives on the nearest ancestor IOUSBHostDevice, not on the
 * IOSerialBSDClient node itself (the driver chain is IOSerialBSDClient -> ... ->
 * IOUSBHostDevice). Walk up a bounded number of levels looking for it. */
static int find_location(io_registry_entry_t node, uint32_t* out_location)
{
    io_registry_entry_t entry = node;
    int                  found = 0;

    for (int depth = 0; depth < 8 && entry != IO_OBJECT_NULL; depth++)
    {
        CFNumberRef lref = (CFNumberRef) IORegistryEntryCreateCFProperty(entry, CFSTR(TB_IOREG_LOCATION_KEY), kCFAllocatorDefault, 0);
        if (lref)
        {
            int32_t l = 0;
            CFNumberGetValue(lref, kCFNumberSInt32Type, &l);
            *out_location = (uint32_t) l;
            CFRelease(lref);
            found = 1;
            break;
        }

        io_registry_entry_t parent = IO_OBJECT_NULL;
        kern_return_t        kr     = IORegistryEntryGetParentEntry(entry, kIOServicePlane, &parent);
        if (entry != node)
            IOObjectRelease(entry);
        if (kr != KERN_SUCCESS)
        {
            entry = IO_OBJECT_NULL;
            break;
        }
        entry = parent;
    }

    /* Single cleanup point for whichever node the loop ended on -- the found-property
     * case (break above) and the depth-bound case (loop condition false) both leave an
     * owned reference in `entry` that the two early-release paths above don't cover;
     * `node` itself is the caller's reference, never ours to release. */
    if (entry != node && entry != IO_OBJECT_NULL)
        IOObjectRelease(entry);

    return found;
}

int tb_usb_resolve(uint32_t location, char* out_path, size_t out_len)
{
    CFMutableDictionaryRef match = IOServiceMatching(TB_IOREG_SERIAL_CLASS);
    if (!match)
        return -1;

    io_iterator_t iter = IO_OBJECT_NULL;
    if (IOServiceGetMatchingServices(kIOMainPortDefault, match, &iter) != KERN_SUCCESS)
        return -1;

    int          rc = -1;
    io_service_t node;
    while ((node = IOIteratorNext(iter)) != IO_OBJECT_NULL)
    {
        uint32_t node_location = 0;
        if (find_location(node, &node_location) && node_location == location)
        {
            CFStringRef pathRef = (CFStringRef) IORegistryEntryCreateCFProperty(node, CFSTR(TB_IOREG_CALLOUT_KEY), kCFAllocatorDefault, 0);
            if (pathRef)
            {
                if (CFStringGetCString(pathRef, out_path, (CFIndex) out_len, kCFStringEncodingUTF8))
                    rc = 0;
                CFRelease(pathRef);
            }
        }

        IOObjectRelease(node);
        if (rc == 0)
            break;
    }

    IOObjectRelease(iter);
    return rc;
}

#else /* !__APPLE__ */

int tb_usb_resolve(uint32_t location, char* out_path, size_t out_len)
{
    (void) location;
    (void) out_path;
    (void) out_len;
    return -1;
}

#endif
