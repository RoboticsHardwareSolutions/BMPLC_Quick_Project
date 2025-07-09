#include "stm32f1xx_hal.h"

void HAL_MspInit(void)
{

  /* System interrupt init*/
  /* PendSV_IRQn interrupt configuration */
  // HAL_NVIC_SetPriority(PendSV_IRQn, 15, 0);
// 
  // /** NOJTAG: JTAG-DP Disabled and SW-DP Enabled
  // */
// 
  __HAL_RCC_AFIO_CLK_ENABLE();
  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_AFIO_REMAP_SWJ_NOJTAG();

}
