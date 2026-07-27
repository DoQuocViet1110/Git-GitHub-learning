#include "LedDriver.h"
#include "stm32f4xx_hal.h"

/* ECU wiring knowledge: on this board, the LED is wired to PA6.
 * Upper layers (Rte/App) never see GPIOA/GPIO_PIN_6 directly. */
#define LEDDRIVER_PORT GPIOA
#define LEDDRIVER_PIN  GPIO_PIN_6

void LedDriver_Init(void)
{
    /* Pin mode/clock already configured by Mcal (MX_GPIO_Init) during MCU init. */
}

void LedDriver_SetState(LedDriver_StateType state)
{
    HAL_GPIO_WritePin(LEDDRIVER_PORT, LEDDRIVER_PIN, (state == LEDDRIVER_ON) ? GPIO_PIN_SET : GPIO_PIN_RESET);
}
