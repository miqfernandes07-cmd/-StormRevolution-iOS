#include "audio/pcm_ring.h"

#include <algorithm>
#include <cstring>
#include <limits>
#include <stdexcept>

namespace storm::audio {

PcmRing::PcmRing(PcmFormat format, std::size_t capacity_frames)
    : format_(format), capacity_(capacity_frames) {
    if (format.sample_rate < 8000 || format.sample_rate > 192000)
        throw std::invalid_argument("PCM_INVALID_SAMPLE_RATE");
    if (format.channels == 0 || format.channels > 8)
        throw std::invalid_argument("PCM_INVALID_CHANNEL_COUNT");
    if (capacity_ == 0 || capacity_ > max_capacity_frames || (capacity_ & (capacity_ - 1)))
        throw std::invalid_argument("PCM_INVALID_CAPACITY");
    // Both factors are bounded above, so multiplication is safe on 32-bit hosts.
    samples_.resize(capacity_ * format_.channels);
}

void PcmRing::add_counter(std::atomic<std::uint64_t>& counter, std::size_t amount) noexcept {
    // Each counter has only one writer, so no fetch-update loop is needed.
    const auto old = counter.load(std::memory_order_relaxed);
    const auto limit = std::numeric_limits<std::uint64_t>::max();
    counter.store(amount > limit - old ? limit : old + amount, std::memory_order_relaxed);
}

void PcmRing::copy_in(const float* source, std::size_t frames, std::uint64_t position) noexcept {
    if (!frames) return;
    const auto slot = std::size_t(position & (capacity_ - 1));
    const auto first = std::min(frames, capacity_ - slot);
    const auto channels = std::size_t(format_.channels);
    std::memcpy(samples_.data() + slot * channels, source, first * channels * sizeof(float));
    if (frames > first)
        std::memcpy(samples_.data(), source + first * channels, (frames - first) * channels * sizeof(float));
}

void PcmRing::copy_out(float* destination, std::size_t frames, std::uint64_t position) noexcept {
    if (!frames) return;
    const auto slot = std::size_t(position & (capacity_ - 1));
    const auto first = std::min(frames, capacity_ - slot);
    const auto channels = std::size_t(format_.channels);
    std::memcpy(destination, samples_.data() + slot * channels, first * channels * sizeof(float));
    if (frames > first)
        std::memcpy(destination + first * channels, samples_.data(), (frames - first) * channels * sizeof(float));
}

IoResult PcmRing::write(const float* interleaved, std::size_t frame_count) noexcept {
    if (frame_count > capacity_) return {0, IoStatus::request_too_large};
    if (!frame_count) return {0, IoStatus::ok};
    if (!interleaved) return {0, IoStatus::invalid_buffer};
    const auto write = write_position_.load(std::memory_order_relaxed);
    const auto read = read_position_.load(std::memory_order_acquire);
    const auto used = std::size_t(write - read);
    const auto accepted = std::min(frame_count, capacity_ - used);
    copy_in(interleaved, accepted, write);
    write_position_.store(write + accepted, std::memory_order_release);
    add_counter(overflow_frames_, frame_count - accepted);
    return {accepted, IoStatus::ok};
}

IoResult PcmRing::read(float* interleaved, std::size_t frame_count) noexcept {
    if (frame_count > capacity_) return {0, IoStatus::request_too_large};
    if (!frame_count) return {0, IoStatus::ok};
    if (!interleaved) return {0, IoStatus::invalid_buffer};
    const auto read = read_position_.load(std::memory_order_relaxed);
    const auto write = write_position_.load(std::memory_order_acquire);
    const auto consumed = std::min(frame_count, std::size_t(write - read));
    copy_out(interleaved, consumed, read);
    // Publish only after all consumed slots have been copied out.
    read_position_.store(read + consumed, std::memory_order_release);
    if (consumed < frame_count)
        std::fill_n(interleaved + consumed * format_.channels,
                    (frame_count - consumed) * format_.channels, 0.0f);
    add_counter(underrun_frames_, frame_count - consumed);
    return {consumed, IoStatus::ok};
}

Counters PcmRing::counters() const noexcept {
    return {overflow_frames_.load(std::memory_order_relaxed),
            underrun_frames_.load(std::memory_order_relaxed)};
}

bool PcmRing::atomics_are_lock_free() const noexcept {
    return write_position_.is_lock_free() && read_position_.is_lock_free() &&
           overflow_frames_.is_lock_free() && underrun_frames_.is_lock_free();
}

} // namespace storm::audio
