#include "Rte_LedBlink.h"
#include "LedDriver.h"
#include "LedBlink.h"

void Rte_Write_LedBlink_LedState(uint8_t state)
{
    LedDriver_SetState(state ? LEDDRIVER_ON : LEDDRIVER_OFF);
}

void Rte_LedBlink_MainFunction(void)
{
    LedBlink_MainFunction();
}
