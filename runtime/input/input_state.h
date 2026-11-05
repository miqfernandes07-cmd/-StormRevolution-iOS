#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <mutex>

namespace storm::input {
struct Snapshot {
    std::uint32_t buttons = 0;
    float lx = 0, ly = 0, rx = 0, ry = 0, lt = 0, rt = 0;
};
class InputState {
public:
    void update(Snapshot value) {
        value.buttons &= 0xF3FFU; // reserved XInput bits are cleared
        value.lx = clamp(value.lx,-1,1); value.ly = clamp(value.ly,-1,1);
        value.rx = clamp(value.rx,-1,1); value.ry = clamp(value.ry,-1,1);
        value.lt = clamp(value.lt,0,1); value.rt = clamp(value.rt,0,1);
        std::lock_guard<std::mutex> lock(mutex_);
        value_ = value;
    }
    Snapshot snapshot() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return value_;
    }
private:
    static float clamp(float v,float low,float high) { return std::isfinite(v) ? std::clamp(v,low,high) : 0; }
    mutable std::mutex mutex_;
    Snapshot value_;
};
} // namespace storm::input
