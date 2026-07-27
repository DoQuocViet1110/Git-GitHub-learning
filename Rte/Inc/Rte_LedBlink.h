#ifndef RTE_RTE_LEDBLINK_H
#define RTE_RTE_LEDBLINK_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Sender/receiver port: SWC LedBlink writes its logical LED state down to Bsw. */
void Rte_Write_LedBlink_LedState(uint8_t state);

/* Task body: invoked by the Os (Bsw/ServiceLayer) on each scheduler tick,
 * dispatches into the LedBlink SWC runnable. Keeps Bsw from calling App directly. */
void Rte_LedBlink_MainFunction(void);

#ifdef __cplusplus
}
#endif

#endif /* RTE_RTE_LEDBLINK_H */
