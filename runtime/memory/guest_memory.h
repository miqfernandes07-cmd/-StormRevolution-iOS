#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace storm::memory {
// Bounded contiguous guest region. This is not a full Xbox virtual address map.
// Allocation is monotonic for bring-up; a title-specific virtual allocator is pending.
class GuestMemory {
public:
    GuestMemory(std::uint32_t base, std::size_t size);
    std::uint32_t allocate(std::size_t size, std::size_t alignment);
    std::uint8_t load8(std::uint32_t address) const;
    std::uint32_t load32(std::uint32_t address) const;
    std::uint64_t load64(std::uint32_t address) const;
    void store8(std::uint32_t address, std::uint8_t value);
    void store32(std::uint32_t address, std::uint32_t value);
    void store64(std::uint32_t address, std::uint64_t value);
    std::size_t size() const noexcept { return bytes_.size(); }
private:
    std::size_t offset(std::uint32_t address, std::size_t length) const;
    std::uint32_t base_;
    std::vector<std::uint8_t> bytes_;
    std::size_t allocated_ = 0;
};
} // namespace storm::memory
