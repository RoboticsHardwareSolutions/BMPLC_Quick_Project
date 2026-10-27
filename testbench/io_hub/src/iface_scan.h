#pragma once

#include <stdbool.h>

#include "config.h"

/* Presence-only check: is the device currently attached? Never opens/captures it.
 * Resolves iface->usb_location via IOKit -- see usb_resolve.h. On success, the
 * resolved /dev path is copied into out_path (NUL-terminated, truncated to
 * out_path_len); out_path is left as an empty string on failure. out_path may be
 * NULL (with out_path_len ignored) if the caller only wants the bool. */
bool tb_iface_detect(const TbIface* iface, char* out_path, size_t out_path_len);
