#pragma once

#include <stdbool.h>

#include "config.h"

/* Presence-only check: is the device currently attached? Never opens/captures it.
 * Resolves iface->usb_location via IOKit -- see usb_resolve.h. */
bool tb_iface_detect(const TbIface* iface);
