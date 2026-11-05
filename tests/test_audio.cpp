#include "audio/pcm_ring.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <thread>
#include <vector>

namespace {
unsigned checks = 0;
void check(bool passed, const char* message) {
    ++checks;
    if (!passed) throw std::runtime_error(message);
}
template<class Function> void rejects(Function fn, const char* message) {
    ++checks;
    try { fn(); } catch (const std::invalid_argument&) { return; }
    throw std::runtime_error(message);
}

void test_format_and_arguments() {
    using namespace storm::audio;
    rejects([] { PcmRing ring({7999, 2}, 8); }, "reject low sample rate");
    rejects([] { PcmRing ring({192001, 2}, 8); }, "reject high sample rate");
    rejects([] { PcmRing ring({48000, 0}, 8); }, "reject zero channels");
    rejects([] { PcmRing ring({48000, 9}, 8); }, "reject excessive channels");
    rejects([] { PcmRing ring({48000, 2}, 0); }, "reject zero capacity");
    rejects([] { PcmRing ring({48000, 2}, 3); }, "reject nonpower capacity");
    rejects([] { PcmRing ring({48000, 2}, PcmRing::max_capacity_frames * 2); }, "reject excessive capacity");
    PcmRing ring({44100, 2}, 4);
    check(ring.capacity() == 4 && ring.format().sample_rate == 44100 && ring.format().channels == 2,
          "retain PCM format");
    check(ring.write(nullptr, 0).status == IoStatus::ok, "empty write permits null");
    check(ring.read(nullptr, 0).status == IoStatus::ok, "empty read permits null");
    check(ring.write(nullptr, 1).status == IoStatus::invalid_buffer, "null write rejected");
    check(ring.read(nullptr, 1).status == IoStatus::invalid_buffer, "null read rejected");
    std::array<float, 10> samples{};
    samples.fill(12);
    check(ring.write(samples.data(), 5).status == IoStatus::request_too_large, "oversize write rejected");
    check(ring.read(samples.data(), 5).status == IoStatus::request_too_large, "oversize read rejected");
    check(ring.read(samples.data(), std::numeric_limits<std::size_t>::max()).status == IoStatus::request_too_large,
          "multiplication overflow rejected before access");
    check(std::all_of(samples.begin(), samples.end(), [](float sample) { return sample == 12; }),
          "invalid read preserves buffer");
    const auto counters = ring.counters();
    check(counters.overflow_frames == 0 && counters.underrun_frames == 0, "invalid calls preserve counters");
}

void test_queue_semantics() {
    using namespace storm::audio;
    PcmRing ring({48000, 2}, 4);
    const std::array<float, 8> input{1, 11, 2, 22, 3, 33, 4, 44};
    std::array<float, 10> output{};
    output.fill(-99);
    auto result = ring.write(input.data(), 3);
    check(result.status == IoStatus::ok && result.transferred_frames == 3, "write three frames");
    result = ring.read(output.data() + 1, 2);
    check(result.status == IoStatus::ok && result.transferred_frames == 2, "read two frames");
    check(output[0] == -99 && output[1] == 1 && output[2] == 11 && output[3] == 2 && output[4] == 22 && output[5] == -99,
          "interleaved channels and read boundaries");
    result = ring.write(input.data(), 4);
    check(result.transferred_frames == 3, "overflow keeps fitting prefix");
    check(ring.counters().overflow_frames == 1, "overflow counts dropped frames");
    result = ring.write(input.data(), 2);
    check(result.transferred_frames == 0 && ring.counters().overflow_frames == 3, "full queue drops newest");
    output.fill(-99);
    result = ring.read(output.data() + 1, 4);
    const std::array<float, 8> expected{3, 33, 1, 11, 2, 22, 3, 33};
    check(result.transferred_frames == 4 && std::equal(expected.begin(), expected.end(), output.begin() + 1),
          "wrapped FIFO retains old data and accepted prefix");
    check(output.front() == -99 && output.back() == -99, "wrapped read respects output boundary");
    result = ring.read(output.data(), 2);
    check(result.transferred_frames == 0 && std::all_of(output.begin(), output.begin() + 4, [](float v) { return v == 0; }),
          "empty read inserts silence");
    check(ring.counters().underrun_frames == 2, "empty read counts missing frames");
    ring.write(input.data(), 1);
    output.fill(-99);
    result = ring.read(output.data(), 4);
    check(result.transferred_frames == 1 && output[0] == 1 && output[1] == 11 &&
              std::all_of(output.begin() + 2, output.begin() + 8, [](float v) { return v == 0; }) && output[8] == -99,
          "partial underrun preserves prefix and fills only requested suffix");
    check(ring.counters().underrun_frames == 5, "partial underrun adds missing frames");
    PcmRing mono({8000, 1}, 1);
    float sample = -0.25f;
    check(mono.write(&sample, 1).transferred_frames == 1, "single frame capacity write");
    float restored = 0;
    check(mono.read(&restored, 1).transferred_frames == 1 && restored == sample, "single frame capacity read");
    PcmRing surround({192000, 8}, 2);
    std::array<float, 16> surround_in{}, surround_out{};
    for (unsigned i = 0; i < surround_in.size(); ++i) surround_in[i] = float(i) / 16;
    surround.write(surround_in.data(), 2);
    surround.read(surround_out.data(), 2);
    check(surround_in == surround_out, "eight channels copied without mixing");
}

void test_concurrent_fifo() {
    using namespace storm::audio;
    PcmRing ring({48000, 2}, 64);
    constexpr std::size_t total_frames = 100000;
    std::atomic<bool> failed{false};
    std::atomic<bool> cancelled{false};
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(15);
    std::thread producer([&] {
        std::array<float, 14> block{};
        std::size_t sent = 0;
        while (sent < total_frames && !cancelled.load(std::memory_order_relaxed)) {
            const auto count = std::min<std::size_t>(7, total_frames - sent);
            for (std::size_t i = 0; i < count; ++i) {
                block[2 * i] = float(sent + i + 1);
                block[2 * i + 1] = -block[2 * i];
            }
            sent += ring.write(block.data(), count).transferred_frames;
            if (std::chrono::steady_clock::now() > deadline) {
                failed.store(true, std::memory_order_relaxed);
                cancelled.store(true, std::memory_order_relaxed);
            }
            std::this_thread::yield();
        }
    });
    std::array<float, 22> block{};
    std::size_t received = 0;
    while (received < total_frames && !cancelled.load(std::memory_order_relaxed)) {
        const auto requested = std::min<std::size_t>(11, total_frames - received);
        const auto result = ring.read(block.data(), requested);
        for (std::size_t i = 0; i < result.transferred_frames; ++i) {
            const auto expected = float(received + i + 1);
            if (block[2 * i] != expected || block[2 * i + 1] != -expected)
                failed.store(true, std::memory_order_relaxed);
        }
        for (std::size_t i = result.transferred_frames * 2; i < requested * 2; ++i)
            if (block[i] != 0) failed.store(true, std::memory_order_relaxed);
        received += result.transferred_frames;
        if (std::chrono::steady_clock::now() > deadline) {
            failed.store(true, std::memory_order_relaxed);
            cancelled.store(true, std::memory_order_relaxed);
        }
        std::this_thread::yield();
    }
    producer.join();
    check(!failed.load() && received == total_frames, "SPSC FIFO ordering and silence under concurrent wraparound");
    std::cout << "audio atomics lock-free on this host: " << (ring.atomics_are_lock_free() ? "yes" : "no") << '\n';
}
}

int main() {
    try {
        test_format_and_arguments();
        test_queue_semantics();
        test_concurrent_fifo();
        std::cout << "audio: " << checks << " checks passed (PCM buffering only; no audio output or XMA)\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "audio test failed: " << error.what() << '\n';
        return 1;
    }
}
