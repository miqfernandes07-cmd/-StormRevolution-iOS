#include "kernel/process_state.h"
#include <algorithm>
#include <stdexcept>

namespace storm::kernel {
ProcessState::ProcessState(memory::AddressSpace& memory,std::uint32_t pib)
    :memory_(memory),type_address_(0) {
    if(!pib || pib%4 || std::uint64_t(pib)+0x60>(UINT64_C(1)<<32))
        throw std::invalid_argument("KERNEL_PROCESS_LAYOUT_INVALID");
    if(!memory_.available(pib,0x60))throw std::invalid_argument("KERNEL_PROCESS_REGION_CONFLICT");
    type_address_=pib+0x2f;
    const std::uint8_t initial=user;
    memory_.map(type_address_,1,memory::Access::read_write,&initial,1);
}
std::uint32_t ProcessState::get_type() const {return std::uint32_t(memory_.load(type_address_,1));}
void ProcessState::set_type(std::uint32_t value) {
    if(value>system)throw std::invalid_argument("KERNEL_PROCESS_TYPE_INVALID");
    memory_.store(type_address_,1,value);
}
std::uint32_t initialize_critical_section(memory::AddressSpace& memory,std::uint32_t address,std::uint32_t spin) {
    if(!address || std::uint64_t(address)+28>(UINT64_C(1)<<32))
        throw std::invalid_argument("KERNEL_CRITICAL_SECTION_RANGE");
    memory.require_access(address,2,memory::Access::read_write);
    memory.require_access(address+4,4,memory::Access::read_write);
    memory.require_access(address+16,12,memory::Access::read_write);
    // Match the pinned reference's uint32 wrap before rounding, including the
    // upper 255 values. This is reference behavior, not hardware qualification.
    const auto units=std::min(std::uint32_t(spin+std::uint32_t(255))>>8,std::uint32_t(255));
    memory.store(address,2,0x100|units);
    memory.store(address+4,4,0);
    memory.store(address+16,4,0xffffffff);
    memory.store(address+20,4,0);
    memory.store(address+24,4,0);
    return 0;
}
} // namespace storm::kernel
