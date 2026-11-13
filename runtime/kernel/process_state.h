#pragma once
#include "memory/address_space.h"
#include <cstdint>

namespace storm::kernel {
// Sparse PIB subset: only the process_type byte at +0x2f is implemented.
// The caller owns/serializes the guest memory for this process lifetime.
// No KTHREAD, TLS, scheduling, or complete process ABI is implied.
class ProcessState {
public:
    enum Type : std::uint32_t { idle = 0, user = 1, system = 2 };
    ProcessState(memory::AddressSpace&, std::uint32_t pib_address);
    ProcessState(const ProcessState&) = delete;
    ProcessState& operator=(const ProcessState&) = delete;
    std::uint32_t get_type() const;
    void set_type(std::uint32_t);
private:
    memory::AddressSpace& memory_;
    std::uint32_t type_address_;
};
// Initializes known fields only. All writes are preflighted. Unknown dispatch
// header bytes/wait-list links are preserved. Enter/Leave/TryEnter are absent.
std::uint32_t initialize_critical_section(memory::AddressSpace&,std::uint32_t address,
                                         std::uint32_t spin_count = 0);
} // namespace storm::kernel
