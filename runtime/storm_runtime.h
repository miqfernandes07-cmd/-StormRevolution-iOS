#ifndef STORM_RUNTIME_H
#define STORM_RUNTIME_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct StormRuntime StormRuntime;
enum StormRuntimeResult {
    STORM_OK = 0,
    STORM_INVALID_ARGUMENT = 1,
    STORM_IO_ERROR = 2,
    STORM_AOT_IMAGE_MISSING = 3,
    STORM_INTERNAL_ERROR = 4
};

/* Lifecycle and last_error calls belong on one owner thread. Input may be updated
 * from controller callbacks. Destroy only after callbacks have been detached. */
StormRuntime* storm_runtime_create(void);
void storm_runtime_destroy(StormRuntime* runtime);
int storm_runtime_start(StormRuntime* runtime, const char* game_directory);
void storm_runtime_stop(StormRuntime* runtime);
/* Borrowed UTF-8 string; valid until the next lifecycle call or destruction. */
const char* storm_runtime_last_error(const StormRuntime* runtime);
/* Button bits use XInput layout. Axes: [-1,1], triggers: [0,1]. */
void storm_runtime_set_input(StormRuntime* runtime, uint32_t buttons,
    float lx, float ly, float rx, float ry, float lt, float rt);
/* Infrastructure only: checked BE memory and vector arithmetic, no game boot. */
int storm_runtime_self_test(void);

#ifdef __cplusplus
}
#endif
#endif
