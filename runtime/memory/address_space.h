#pragma once
#include <cstddef>
#include <cstdint>
#include <map>
#include <stdexcept>
#include <vector>

namespace storm::memory {
enum class Access : unsigned { read = 1, read_write = 3 };
enum class MemoryFaultKind { invalid_range, overlap, unmapped, read_only, invalid_buffer };
class MemoryFault : public std::runtime_error {
public:
    MemoryFault(MemoryFaultKind, std::uint32_t address, std::size_t length);
    MemoryFaultKind kind() const noexcept { return kind_; }
    std::uint32_t address() const noexcept { return address_; }
    std::size_t length() const noexcept { return length_; }
private:
    MemoryFaultKind kind_;
    std::uint32_t address_;
    std::size_t length_;
};
// Sparse, owned byte regions in the 32-bit guest address space. No host executable
// mappings, MMIO, paging, reservation atomics or hardware alias semantics yet.
// Map/unmap require external synchronization. Callers must serialize conflicting
// data accesses; these copies do not implement Xbox interlocked operations.
class AddressSpace {
public:
    void map(std::uint32_t address, std::size_t size, Access,
             const std::uint8_t* initial = nullptr, std::size_t initial_size = 0);
    void require_access(std::uint32_t address, std::size_t size, Access) const;
    bool available(std::uint32_t address, std::size_t size) const;
    void unmap(std::uint32_t region_start);
    void copy_in(std::uint32_t address, const void* source, std::size_t size);
    void copy_out(std::uint32_t address, void* destination, std::size_t size) const;
    std::uint64_t load(std::uint32_t address, unsigned width) const;
    void store(std::uint32_t address, unsigned width, std::uint64_t value);
    std::size_t mapped_bytes() const noexcept { return mapped_bytes_; }
private:
    struct Region { Access access; std::vector<std::uint8_t> bytes; };
    using Regions = std::map<std::uint32_t, Region>;
    Regions regions_;
    std::size_t mapped_bytes_ = 0;
    static void range(std::uint32_t, std::size_t);
    Regions::const_iterator containing(std::uint32_t) const;
    void validate(std::uint32_t address, std::size_t size, bool write) const;
};
} // namespace storm::memory
