#pragma once
#include "input/input_state.h"
#include <algorithm>
#include <cmath>

namespace storm::input::xbox360 {
// Xbox 360/XInput bit positions. LT/RT are analog values, never button bits.
enum Button : std::uint32_t {
    up = 0x0001, down = 0x0002, left = 0x0004, right = 0x0008,
    start = 0x0010, back = 0x0020, left_stick = 0x0040,
    right_stick = 0x0080, left_shoulder = 0x0100, right_shoulder = 0x0200,
    a = 0x1000, b = 0x2000, x = 0x4000, y = 0x8000
};
constexpr std::uint32_t known_buttons = 0xf3ff;
inline float bounded(float value, float low, float high) noexcept {
    return std::isfinite(value) ? std::clamp(value, low, high) : 0;
}
inline Snapshot sanitized(Snapshot value) noexcept {
    value.buttons &= known_buttons;
    value.lx = bounded(value.lx, -1, 1); value.ly = bounded(value.ly, -1, 1);
    value.rx = bounded(value.rx, -1, 1); value.ry = bounded(value.ry, -1, 1);
    value.lt = bounded(value.lt, 0, 1); value.rt = bounded(value.rt, 0, 1);
    return value;
}
// A physical stick takes precedence as a pair outside the deadzone. Mixing
// its X axis with touch Y changes directions unexpectedly, so never do that.
// Below the deadzone it contributes no axes; touch remains usable concurrently.
inline Snapshot combine(Snapshot touch, Snapshot physical) noexcept {
    touch = sanitized(touch); physical = sanitized(physical);
    Snapshot result = touch;
    result.buttons |= physical.buttons;
    if (physical.lx * physical.lx + physical.ly * physical.ly > .01f) {
        result.lx = physical.lx; result.ly = physical.ly;
    }
    if (physical.rx * physical.rx + physical.ry * physical.ry > .01f) {
        result.rx = physical.rx; result.ry = physical.ry;
    }
    result.lt = std::max(touch.lt, physical.lt);
    result.rt = std::max(touch.rt, physical.rt);
    return result;
}
} // namespace storm::input::xbox360
