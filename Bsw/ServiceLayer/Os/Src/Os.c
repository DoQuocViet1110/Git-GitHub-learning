#include "Os.h"
#include "Rte_LedBlink.h"
#include "stm32f4xx_hal.h"

#define OS_LEDBLINK_PERIOD_MS 500U

static uint32_t Os_LedBlinkLastTick;

void Os_Init(void)
{
    Os_LedBlinkLastTick = HAL_GetTick();
}

void Os_Schedule(void)
{
    uint32_t now = HAL_GetTick();

    if ((now - Os_LedBlinkLastTick) >= OS_LEDBLINK_PERIOD_MS)
    {
        Os_LedBlinkLastTick = now;
        Rte_LedBlink_MainFunction();
    }
}
