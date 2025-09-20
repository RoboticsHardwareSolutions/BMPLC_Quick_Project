
// If we could guess an MG_ARCH so far, preserve it, otherwise try GCC-based
#if defined(MG_ARCH)
#    define MG_STMPACK_ARCH MG_ARCH
#    undef MG_ARCH
#elif defined(__GNUC__)
#    define MG_STMPACK_ARCH MG_ARCH_NEWLIB
#endif

#define MG_ENABLE_PACKED_FS 1
#define MG_ENABLE_CUSTOM_MILLIS 0
#define MG_ENABLE_MBEDTLS 0
#define MG_ARCH MG_ARCH_FREERTOS
#define MG_ENABLE_CUSTOM_RANDOM 1

#define MG_ENABLE_TCPIP 1
#define MG_ENABLE_DRIVER_STM32F 1
// MG_ENABLE_TCPIP_DRIVER_INIT if 1 (by default), call MG_TCPIP_DRIVER_INIT(&mgr) in mg_mgr_init().
// If 0, call it manually later. Useful if you need several mgr, e.g. for dual interfaces (Eth + USB + WiFi)
#define MG_ENABLE_TCPIP_DRIVER_INIT 0

#define MG_TCPIP_PHY_ADDR 1
#define MG_DRIVER_MDC_CR 4

// For static IP configuration, define MG_TCPIP_{IP,MASK,GW}
// By default, those are set to zero, meaning that DHCP is used
//
#define MG_TCPIP_IP MG_IPV4(192, 168, 1, 101)
#define MG_TCPIP_GW MG_IPV4(192, 168, 1, 1)
#define MG_TCPIP_MASK MG_IPV4(255, 255, 255, 0)

// Construct MAC address from the MCU unique ID. It is defined in the
// ST CMSIS header as UID_BASE
#define MGUID ((uint32_t*) 0x1FFF7A10)  // Unique 96-bit chip ID
#define MG_SET_MAC_ADDRESS(mac)          \
    do                                   \
    {                                    \
        mac[0] = 2;                      \
        mac[1] = MGUID[0] & 255;         \
        mac[2] = (MGUID[0] >> 10) & 255; \
        mac[3] = (MGUID[0] >> 19) & 255; \
        mac[4] = MGUID[1] & 255;         \
        mac[5] = MGUID[2] & 255;         \
    } while (0)

#if MG_ENABLE_PACKED_FS
#    define MG_ENABLE_FILE 0
#endif

// See https://mongoose.ws/documentation/#build-options
