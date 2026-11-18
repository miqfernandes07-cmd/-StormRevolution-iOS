#pragma once
#include <cstddef>
#include <cstdint>
#include <functional>
#include <map>
#include <stdexcept>
#include <vector>

namespace storm::memory {
enum class Access : unsigned { read = 1, read_write = 3 };
enum class MemoryFaultKind { invalid_range, overlap, unmapped, read_only, invalid_buffer, unsupported_atomic };
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
    // Serialized guest32 reservation model; writes to the tracked 128-byte
    // granule invalidate all earlier tokens, including same-value/ABA writes.
    class Reservation {
        friend class AddressSpace;
        const AddressSpace* owner_=nullptr;
        std::uint32_t address_=0;
        std::uint64_t version_=0;
    public:
        void clear() noexcept {owner_=nullptr;}
    };
    std::uint32_t reserve_load32(std::uint32_t address,Reservation&);
    bool conditional_store32(std::uint32_t address,std::uint32_t value,Reservation&);
    void map(std::uint32_t address, std::size_t size, Access,
             const std::uint8_t* initial = nullptr, std::size_t initial_size = 0);
    // Serialized read-only field provider. Called with region-relative offsets.
    // Providers must fill every requested byte and must not mutate/remap this
    // AddressSpace. Exceptions leave copy_out destinations unchanged.
    using ReadProvider=std::function<void(std::size_t,std::uint8_t*,std::size_t)>;
    void map_reader(std::uint32_t address,std::size_t size,ReadProvider);
    void require_access(std::uint32_t address, std::size_t size, Access) const;
    bool available(std::uint32_t address, std::size_t size) const;
    void unmap(std::uint32_t region_start);
    void copy_in(std::uint32_t address, const void* source, std::size_t size);
    void copy_out(std::uint32_t address, void* destination, std::size_t size) const;
    std::uint64_t load(std::uint32_t address, unsigned width) const;
    void store(std::uint32_t address, unsigned width, std::uint64_t value);
    std::size_t mapped_bytes() const noexcept { return mapped_bytes_; }
private:
    struct Region { Access access; std::vector<std::uint8_t> bytes; ReadProvider reader; };
    using Regions = std::map<std::uint32_t, Region>;
    Regions regions_;
    std::size_t mapped_bytes_ = 0;
    std::map<std::uint32_t,std::uint64_t> reservation_versions_;
    void invalidate_reservations(std::uint32_t,std::size_t);
    void require_reservable(std::uint32_t,bool write) const;
    static void range(std::uint32_t, std::size_t);
    Regions::const_iterator containing(std::uint32_t) const;
    void validate(std::uint32_t address, std::size_t size, bool write) const;
};
} // namespace storm::memory
