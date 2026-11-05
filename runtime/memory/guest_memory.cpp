#include "memory/guest_memory.h"
#include <limits>
#include <stdexcept>

namespace storm::memory {
GuestMemory::GuestMemory(std::uint32_t base, std::size_t size) : base_(base) {
    constexpr std::uint64_t address_space = std::uint64_t{1} << 32;
    if (size == 0 || size > 1024ULL*1024*1024 || size > address_space-base)
        throw std::invalid_argument("GUEST_MEMORY_INVALID_REGION");
    bytes_.resize(size, 0);
}
std::size_t GuestMemory::offset(std::uint32_t address, std::size_t length) const {
    if (address < base_) throw std::out_of_range("GUEST_MEMORY_BOUNDS");
    const std::size_t start = address - base_;
    if (start > bytes_.size() || length > bytes_.size()-start)
        throw std::out_of_range("GUEST_MEMORY_BOUNDS");
    return start;
}
std::uint32_t GuestMemory::allocate(std::size_t size, std::size_t alignment) {
    if (!size || !alignment || (alignment & (alignment-1)) || alignment > (1ULL<<32))
        throw std::invalid_argument("GUEST_ALLOCATION_ALIGNMENT_OR_SIZE");
    const std::uint64_t current = std::uint64_t(base_) + allocated_;
    const std::uint64_t start = (current + alignment - 1) & ~(std::uint64_t(alignment)-1);
    const std::uint64_t limit = std::uint64_t(base_) + bytes_.size();
    if (start > limit || size > limit-start || start > std::numeric_limits<std::uint32_t>::max())
        throw std::bad_alloc();
    allocated_ = std::size_t(start-base_) + size;
    return std::uint32_t(start);
}
std::uint8_t GuestMemory::load8(std::uint32_t address) const { return bytes_[offset(address,1)]; }
std::uint32_t GuestMemory::load32(std::uint32_t address) const {
    const auto i = offset(address,4);
    return (std::uint32_t(bytes_[i])<<24) | (std::uint32_t(bytes_[i+1])<<16) |
           (std::uint32_t(bytes_[i+2])<<8) | bytes_[i+3];
}
std::uint64_t GuestMemory::load64(std::uint32_t address) const {
    const auto i = offset(address,8);
    std::uint64_t value = 0;
    for (unsigned j=0; j<8; ++j) value = (value<<8) | bytes_[i+j];
    return value;
}
void GuestMemory::store8(std::uint32_t address, std::uint8_t value) { bytes_[offset(address,1)] = value; }
void GuestMemory::store32(std::uint32_t address, std::uint32_t value) {
    const auto i = offset(address,4);
    for (unsigned j=0; j<4; ++j) bytes_[i+j] = std::uint8_t(value >> (24-j*8));
}
void GuestMemory::store64(std::uint32_t address, std::uint64_t value) {
    const auto i = offset(address,8);
    for (unsigned j=0; j<8; ++j) bytes_[i+j] = std::uint8_t(value >> (56-j*8));
}
} // namespace storm::memory
