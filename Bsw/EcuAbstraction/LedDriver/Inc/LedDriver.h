#ifndef BSW_ECUABSTRACTION_LEDDRIVER_LEDDRIVER_H
#define BSW_ECUABSTRACTION_LEDDRIVER_LEDDRIVER_H

#ifdef __cplusplus
extern "C" {
#endif

typedef enum
{
    LEDDRIVER_OFF = 0,
    LEDDRIVER_ON  = 1
} LedDriver_StateType;

void LedDriver_Init(void);
void LedDriver_SetState(LedDriver_StateType state);

#ifdef __cplusplus
}
#endif

#endif /* BSW_ECUABSTRACTION_LEDDRIVER_LEDDRIVER_H */
