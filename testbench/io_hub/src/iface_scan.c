#include "iface_scan.h"

#include "usb_resolve.h"

bool tb_iface_detect(const TbIface* iface, char* out_path, size_t out_path_len)
{
    if (out_path && out_path_len)
        out_path[0] = '\0';

    if (iface->usb_location == 0)
        return false;

    char   local_path[256];
    char*  path     = out_path ? out_path : local_path;
    size_t path_len = out_path ? out_path_len : sizeof(local_path);
    return tb_usb_resolve(iface->usb_location, path, path_len) == 0;
}
