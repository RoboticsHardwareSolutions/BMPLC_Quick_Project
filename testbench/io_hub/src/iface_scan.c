#include "iface_scan.h"

#include "usb_resolve.h"

bool tb_iface_detect(const TbIface* iface)
{
    if (iface->usb_location == 0)
        return false;

    char path[256];
    return tb_usb_resolve(iface->usb_location, path, sizeof(path)) == 0;
}
