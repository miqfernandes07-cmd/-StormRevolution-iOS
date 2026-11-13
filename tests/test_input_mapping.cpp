#include "input/xbox360_mapping.h"
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

int main() {
    using namespace storm::input;
    using namespace storm::input::xbox360;
    unsigned checks = 0;
    auto check = [&](bool result) {
        if (!result) throw std::runtime_error("Xbox 360 input check " + std::to_string(checks));
        ++checks;
    };
    try {
        check((up | down | left | right | start | back | left_stick | right_stick |
               left_shoulder | right_shoulder | a | b | x | y) == known_buttons);
        check(a == 4096 && b == 8192 && x == 16384 && y == 32768);
        Snapshot touch{a | back, -.8f, .7f, .4f, -.3f, 1, 0};
        Snapshot physical{b | start | left_stick | right_stick, .5f, 0, 0, -.8f, .4f, .7f};
        auto result = combine(touch, physical);
        check(result.buttons == (a | b | back | start | left_stick | right_stick));
        check(result.lx == .5f && result.ly == 0); // do not borrow touch Y
        check(result.rx == 0 && result.ry == -.8f); // do not borrow touch X
        check(result.lt == 1 && result.rt == .7f);
        physical.lx = .05f; physical.ly = -.05f; physical.rx = physical.ry = 0;
        result = combine(touch, physical);
        check(result.lx == -.8f && result.ly == .7f);
        check(result.rx == .4f && result.ry == -.3f);
        physical.lx = physical.ly = .08f; // radial, not per-axis deadzone
        result = combine(touch, physical);
        check(result.lx == .08f && result.ly == .08f);
        result = combine(touch, {}); // disconnect releases only physical state
        check(result.buttons == (a | back) && result.lx == -.8f && result.ly == .7f);
        check(result.rx == .4f && result.ry == -.3f && result.lt == 1 && result.rt == 0);
        result = combine({}, {}); // inactive app clears all sources
        check(result.buttons == 0 && result.lx == 0 && result.ly == 0 && result.rx == 0 &&
              result.ry == 0 && result.lt == 0 && result.rt == 0);
        const float nan = std::numeric_limits<float>::quiet_NaN();
        result = combine({0xffffffff, nan, 5, -3, nan, -1, 8}, {});
        check(result.buttons == known_buttons && result.lx == 0 && result.ly == 1);
        check(result.rx == -1 && result.ry == 0 && result.lt == 0 && result.rt == 1);
        for (unsigned bit = 0; bit < 16; ++bit) {
            result = combine({1u << bit}, {});
            check(result.buttons == ((1u << bit) & known_buttons));
        }
        // Triggers remain independent of the bitfield across their full range.
        for (unsigned i = 0; i <= 1000; ++i) {
            float v = float(i) / 1000;
            result = combine({0, 0, 0, 0, 0, v, 0}, {0, 0, 0, 0, 0, 0, 1 - v});
            check(result.buttons == 0 && result.lt == v && result.rt == 1 - v);
        }
        std::cout << "Xbox 360 input mapping: " << checks << " checks passed; no controller hardware tested\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n'; return 1;
    }
}
