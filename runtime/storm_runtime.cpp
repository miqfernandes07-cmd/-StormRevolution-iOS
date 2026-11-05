#include "storm_runtime.h"
#include "cpu/context.h"
#include "filesystem/content_root.h"
#include "input/input_state.h"
#include "memory/guest_memory.h"
#include <filesystem>
#include <new>
#include <string>

struct StormRuntime {
    std::string error;
    storm::input::InputState input;
};

extern "C" StormRuntime* storm_runtime_create(void) {
    try { return new StormRuntime; } catch (...) { return nullptr; }
}
extern "C" void storm_runtime_destroy(StormRuntime* runtime) { delete runtime; }
extern "C" int storm_runtime_start(StormRuntime* runtime,const char* directory) {
    if (!runtime) return STORM_INVALID_ARGUMENT;
    // No allocations or filesystem exceptions may cross the C/Objective-C ABI.
    try {
        if (!directory || !*directory) {
            runtime->error = "RUNTIME_INVALID_GAME_DIRECTORY";
            return STORM_INVALID_ARGUMENT;
        }
        const storm::filesystem::ContentRoot content(directory);
        if (!std::filesystem::is_regular_file(content.resolve("default.xex"))) {
            runtime->error = "RUNTIME_DEFAULT_XEX_MISSING";
            return STORM_IO_ERROR;
        }
        runtime->error = "RUNTIME_AOT_IMAGE_MISSING: no Storm Revolution executable has been recompiled and linked. Game execution is unavailable.";
        return STORM_AOT_IMAGE_MISSING;
    } catch (const std::bad_alloc&) {
        return STORM_INTERNAL_ERROR;
    } catch (const std::exception&) {
        try { runtime->error = "RUNTIME_CONTENT_ACCESS_FAILED"; } catch (...) {}
        return STORM_IO_ERROR;
    } catch (...) { return STORM_INTERNAL_ERROR; }
}
extern "C" void storm_runtime_stop(StormRuntime* runtime) {
    if (!runtime) return;
    try { runtime->input.update({}); runtime->error.clear(); } catch (...) {}
}
extern "C" const char* storm_runtime_last_error(const StormRuntime* runtime) {
    return runtime ? runtime->error.c_str() : "RUNTIME_NULL_HANDLE";
}
extern "C" void storm_runtime_set_input(StormRuntime* runtime,std::uint32_t buttons,
    float lx,float ly,float rx,float ry,float lt,float rt) {
    if (!runtime) return;
    try { runtime->input.update({buttons,lx,ly,rx,ry,lt,rt}); } catch (...) {}
}
extern "C" int storm_runtime_self_test(void) {
    try {
        storm::memory::GuestMemory memory(0x1000,64);
        memory.store32(0x1000,0x12345678);
        if (memory.load8(0x1000) != 0x12 || memory.load32(0x1000) != 0x12345678) return 1;
        storm::cpu::Vector128 a,b;
        a.set_word(0,0xFFFFFFFF); b.set_word(0,1);
        if (storm::cpu::add_u32(a,b).word(0) != 0) return 2;
        return 0;
    } catch (...) { return 3; }
}
