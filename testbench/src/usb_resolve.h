#pragma once

#include <stddef.h>
#include <stdint.h>

/* Resolves a USB device's physical hub port (IOKit "locationID" -- encodes the exact
 * port path through the USB tree, stable across reboots and serial-number quirks of
 * cheap USB-serial clones, but changes if the cable is moved to a different hub port)
 * to its currently-enumerated callout device path (e.g. "/dev/cu.usbserial-140").
 * Returns 0 and fills out_path on success, -1 if no attached device currently matches.
 * macOS-only (IOKit); on other platforms always returns -1. */
int tb_usb_resolve(uint32_t location, char* out_path, size_t out_len);
