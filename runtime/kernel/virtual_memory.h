#pragma once
#include "memory/address_space.h"
#include <cstdint>
#include <map>

namespace storm::kernel {
class VirtualMemory {
public:
    static constexpr std::uint32_t success=0,invalid_parameter=0xc000000d,
        no_memory=0xc0000017,conflicting_addresses=0xc0000018;
    explicit VirtualMemory(memory::AddressSpace& space):space_(space) {}
    // Caller serializes requests and owns the heap pools. Output references are
    // changed only on success. Guest ABI adapters must validate output pointers.
    std::uint32_t allocate(std::uint32_t& base,std::uint32_t& size,std::uint32_t flags,
                           std::uint32_t protection,std::uint32_t debug_memory);
    std::uint32_t free(std::uint32_t& base,std::uint32_t& size,std::uint32_t flags);
    std::uint32_t allocate_guest(std::uint32_t base_pointer,std::uint32_t size_pointer,
        std::uint32_t flags,std::uint32_t protection,std::uint32_t debug_memory);
    std::uint32_t free_guest(std::uint32_t base_pointer,std::uint32_t size_pointer,std::uint32_t flags);
    std::size_t committed_bytes() const noexcept { return committed_bytes_; }
    std::size_t reservations() const noexcept { return allocations_.size(); }
private:
    struct Allocation {
        std::uint32_t size,page;
        std::map<std::uint32_t,memory::Access> committed;
    };
    memory::AddressSpace& space_;
    std::map<std::uint32_t,Allocation> allocations_;
    std::size_t committed_bytes_ = 0;
    bool available(std::uint32_t,std::uint32_t) const;
};
} // namespace storm::kernel
