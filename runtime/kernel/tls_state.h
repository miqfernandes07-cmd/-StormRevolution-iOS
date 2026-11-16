#pragma once
#include "memory/address_space.h"
#include <cstdint>
#include <map>
#include <vector>

namespace storm::kernel {
// Map only PCR+0x100 -> KTHREAD and KTHREAD+0x14c -> numeric thread ID.
// Both known prefixes must be free/disjoint; other fields remain inaccessible.
void map_thread_identity(memory::AddressSpace&,std::uint32_t pcr,
                         std::uint32_t kthread,std::uint32_t thread_id);
// Serialized dynamic TLS subset. Process-wide slot allocation, per-thread BE32
// storage. Does not initialize static XEX TLS, KTHREAD, PCR/r13 or a scheduler.
class DynamicTls {
public:
    static constexpr std::uint32_t out_of_indexes=0xffffffff;
    DynamicTls(memory::AddressSpace&,std::uint32_t slot_count);
    DynamicTls(const DynamicTls&)=delete;
    DynamicTls& operator=(const DynamicTls&)=delete;
    void attach(std::uint32_t thread,std::uint32_t guest_base);
    std::uint32_t allocate(std::uint32_t thread);
    bool free(std::uint32_t slot);
    std::uint32_t get(std::uint32_t thread,std::uint32_t slot) const;
    void set(std::uint32_t thread,std::uint32_t slot,std::uint32_t value);
private:
    memory::AddressSpace& memory_;
    std::vector<bool> allocated_;
    std::map<std::uint32_t,std::uint32_t> threads_;
    std::uint32_t address(std::uint32_t thread,std::uint32_t slot) const;
};
} // namespace storm::kernel
