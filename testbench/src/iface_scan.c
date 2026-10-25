#include "iface_scan.h"

#include <stddef.h>
#include <unistd.h>

bool tb_iface_detect(const char* port)
{
    if (!port || port[0] == '\0')
        return false;
    return access(port, F_OK) == 0;
}
