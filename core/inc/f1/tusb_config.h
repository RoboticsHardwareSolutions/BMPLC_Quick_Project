#pragma once

#define TUD_OPT_RHPORT          0
#define CFG_TUSB_MCU            OPT_MCU_STM32F1
#define CFG_TUSB_OS             OPT_OS_FREERTOS
#define CFG_TUSB_DEBUG          0
#define CFG_TUH_ENABLED         0
#define CFG_TUD_ENABLED         1
#define CFG_TUD_ENDPOINT0_SIZE  64
// #define CFG_TUD_ECM_RNDIS       1

#define CFG_TUD_CDC               2
#define CFG_TUD_CDC_NOTIFY        1 // Enable use of notification endpoint

// CDC FIFO size of TX and RX
#define CFG_TUD_CDC_RX_BUFSIZE   (32)
#define CFG_TUD_CDC_TX_BUFSIZE   (32)

// CDC Endpoint transfer buffer size, more is faster
#define CFG_TUD_CDC_EP_BUFSIZE   (32)

// String Descriptor Index
enum
{
    STRID_LANGID = 0,
    STRID_MANUFACTURER,
    STRID_PRODUCT,
    STRID_SERIAL,
    STRID_INTERFACE,
    STRID_MAC
};
