/* This header necessary for usb lib */
#ifndef _STM32_H_
#define _STM32_H_

/* modify bitfield */
#define _BMD(reg, msk, val) (reg) = (((reg) & ~(msk)) | (val))
/* set bitfield */
#define _BST(reg, bits)     (reg) = ((reg) | (bits))
/* clear bitfield */
#define _BCL(reg, bits)     (reg) = ((reg) & ~(bits))
/* wait until bitfield set */
#define _WBS(reg, bits)     while(((reg) & (bits)) == 0)
/* wait until bitfield clear */
#define _WBC(reg, bits)     while(((reg) & (bits)) != 0)
/* wait for bitfield value */
#define _WVL(reg, msk, val) while(((reg) & (msk)) != (val))
/* bit value */
#define _BV(bit)            (0x01 << (bit))

#if defined(STM32F103xE)
#    include "stm32f1xx.h"
#    include <stm32f1xx_ll_pwr.h>
#    include <stm32f1xx_ll_rcc.h>
#    include <stm32f1xx_ll_gpio.h>
#elif defined(STM32F405xx) || defined(STM32F407xx)
#    include "stm32f4xx.h"
#    include <stm32f4xx_ll_pwr.h>
#    include <stm32f4xx_ll_rcc.h>
#    include <stm32f4xx_ll_gpio.h>
#endif

#endif // _STM32_H_
