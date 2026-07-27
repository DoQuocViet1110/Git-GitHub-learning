#ifndef APP_LEDBLINK_LEDBLINK_H
#define APP_LEDBLINK_LEDBLINK_H

#ifdef __cplusplus
extern "C" {
#endif

/* SWC lifecycle: called once during startup. */
void LedBlink_Init(void);

/* SWC runnable: called periodically by Rte_LedBlink_MainFunction. */
void LedBlink_MainFunction(void);

#ifdef __cplusplus
}
#endif

#endif /* APP_LEDBLINK_LEDBLINK_H */
