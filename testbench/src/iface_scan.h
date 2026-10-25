#pragma once

#include <stdbool.h>

/* Presence-only check: does the device node at `port` exist? Never opens/captures it. */
bool tb_iface_detect(const char* port);
