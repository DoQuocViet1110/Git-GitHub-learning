#include "LedBlink.h"
#include "Rte_LedBlink.h"
#include <stdint.h>

static uint8_t LedBlink_State;

void LedBlink_Init(void)
{
    LedBlink_State = 0;
    Rte_Write_LedBlink_LedState(LedBlink_State);
}

void LedBlink_MainFunction(void)
{
    LedBlink_State ^= 1u;
    Rte_Write_LedBlink_LedState(LedBlink_State);
}
