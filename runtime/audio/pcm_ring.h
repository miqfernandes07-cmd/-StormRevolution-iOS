#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace storm::audio {

struct PcmFormat {
    std::uint32_t sample_rate = 48000;
    std::uint32_t channels = 2;
};

enum class IoStatus { ok, invalid_buffer, request_too_large };
struct IoResult {
    std::size_t transferred_frames;
    IoStatus status;
};
struct Counters {
    std::uint64_t overflow_frames;
    std::uint64_t underrun_frames;
};

// One producer calls write(); one consumer calls read(). Concurrent writers or
// concurrent readers are forbidden. Interleaved float PCM is copied verbatim.
// Constructor allocates; write/read do not allocate, lock a mutex, or throw.
// Destructor requires both threads/callbacks to have stopped.
class PcmRing {
public:
    static constexpr std::size_t max_capacity_frames = 1U << 20;
    // Sample rate: 8,000..192,000 Hz; channels: 1..8; capacity: power of two.
    explicit PcmRing(PcmFormat format, std::size_t capacity_frames);
    PcmRing(const PcmRing&) = delete;
    PcmRing& operator=(const PcmRing&) = delete;

    // frame_count must not exceed capacity(). Null is allowed only for zero
    // frames. Invalid calls leave buffers, queue positions and counters intact.
    // Writes keep the prefix that fits, dropping newest excess frames.
    IoResult write(const float* interleaved, std::size_t frame_count) noexcept;
    // Reads consume the available prefix and zero-fill all missing frames.
    // transferred_frames excludes silence inserted for an underrun.
    IoResult read(float* interleaved, std::size_t frame_count) noexcept;

    PcmFormat format() const noexcept { return format_; }
    std::size_t capacity() const noexcept { return capacity_; }
    // Diagnostic counters saturate at UINT64_MAX. The two values are sampled
    // independently; this is not a simultaneous snapshot of stream position.
    Counters counters() const noexcept;
    bool atomics_are_lock_free() const noexcept;

private:
    static void add_counter(std::atomic<std::uint64_t>& counter, std::size_t amount) noexcept;
    void copy_in(const float* source, std::size_t frames, std::uint64_t position) noexcept;
    void copy_out(float* destination, std::size_t frames, std::uint64_t position) noexcept;

    const PcmFormat format_;
    const std::size_t capacity_;
    std::vector<float> samples_;
    // Each index is owned by one thread; acquire/release protects slot reuse.
    // Power-of-two capacity keeps slot mapping correct across uint64 rollover.
    alignas(64) std::atomic<std::uint64_t> write_position_{0};
    alignas(64) std::atomic<std::uint64_t> read_position_{0};
    alignas(64) std::atomic<std::uint64_t> overflow_frames_{0};
    alignas(64) std::atomic<std::uint64_t> underrun_frames_{0};
};

} // namespace storm::audio
