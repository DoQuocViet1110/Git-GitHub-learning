#ifndef BSW_SERVICELAYER_OS_OS_H
#define BSW_SERVICELAYER_OS_OS_H

#ifdef __cplusplus
extern "C" {
#endif

void Os_Init(void);

/* Cooperative scheduler tick: call repeatedly from the main super-loop.
 * Dispatches periodic tasks (via Rte) when their period has elapsed. */
void Os_Schedule(void);

#ifdef __cplusplus
}
#endif

#endif /* BSW_SERVICELAYER_OS_OS_H */
