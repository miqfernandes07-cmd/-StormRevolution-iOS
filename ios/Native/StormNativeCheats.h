#pragma once
#include <stdbool.h>
#ifdef __cplusplus
extern "C" {
#endif
// Implemented by private title hooks. Set once, before launching any guest thread.
void StormNativeSetCheatsEnabled(bool enabled);
#ifdef __cplusplus
}
#endif
