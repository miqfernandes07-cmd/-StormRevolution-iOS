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
HardwareInfo::HardwareInfo(memory::AddressSpace& memory,std::uint32_t address,
                           std::uint32_t flags,std::uint8_t cpus)
    :memory_(memory),address_(address) {
    if(!address || address%4 || std::uint64_t(address)+16>(UINT64_C(1)<<32) || !cpus || cpus>6)
        throw std::invalid_argument("KERNEL_HARDWARE_LAYOUT_INVALID");
    if(!memory.available(address,16))throw std::invalid_argument("KERNEL_HARDWARE_REGION_CONFLICT");
    const std::uint8_t bytes[]={std::uint8_t(flags>>24),std::uint8_t(flags>>16),
                              std::uint8_t(flags>>8),std::uint8_t(flags),cpus};
    memory.map(address,5,memory::Access::read,bytes,5);
}
void HardwareInfo::bind_import(std::uint32_t slot,std::uint32_t expected) {
    if(!slot || slot%4 || expected>>24 || (expected&65535)!=0x156 || memory_.load(slot,4)!=expected)
        throw std::invalid_argument("KERNEL_HARDWARE_IMPORT_MISMATCH");
    memory_.store(slot,4,address_);
}
namespace {
struct LockState {std::uint32_t count, recursion, owner;};
LockState lock_state(memory::AddressSpace& memory,std::uint32_t address) {
    if(!address || address%4 || std::uint64_t(address)+28>(UINT64_C(1)<<32))
        throw std::invalid_argument("KERNEL_CRITICAL_SECTION_RANGE");
    if(memory.load(address,1)!=1)throw std::invalid_argument("KERNEL_CRITICAL_SECTION_TYPE");
    LockState state{std::uint32_t(memory.load(address+16,4)),
                    std::uint32_t(memory.load(address+20,4)),std::uint32_t(memory.load(address+24,4))};
    if(state.count==0xffffffff) {
        if(state.recursion || state.owner)throw std::invalid_argument("KERNEL_CRITICAL_SECTION_STATE");
    } else if(state.count>0x7fffffff || !state.recursion || state.recursion>0x7fffffff ||
              !state.owner || state.count<state.recursion-1) {
        throw std::invalid_argument("KERNEL_CRITICAL_SECTION_STATE");
    }
    return state;
}
void write_lock(memory::AddressSpace& memory,std::uint32_t address,LockState state) {
    memory.require_access(address+16,12,memory::Access::read_write);
    memory.store(address+16,4,state.count);
    memory.store(address+20,4,state.recursion);
    memory.store(address+24,4,state.owner);
}
}
CriticalSections::CriticalSections(memory::AddressSpace& memory,std::uint32_t thread)
    :memory_(memory),thread_(thread) {
    if(!thread || thread%4)throw std::invalid_argument("KERNEL_THREAD_IDENTITY_REQUIRED");
}
bool CriticalSections::try_enter(std::uint32_t address) {
    auto state=lock_state(memory_,address);
    if(state.count==0xffffffff) {
        write_lock(memory_,address,{0,1,thread_});return true;
    }
    if(state.owner!=thread_)return false;
    if(state.count!=state.recursion-1)
        throw std::runtime_error("KERNEL_CRITICAL_SECTION_WAITERS_REQUIRE_SCHEDULER");
    if(state.recursion==0x7fffffff)
        throw std::runtime_error("KERNEL_CRITICAL_SECTION_RECURSION_LIMIT");
    write_lock(memory_,address,{state.count+1,state.recursion+1,thread_});return true;
}
void CriticalSections::enter(std::uint32_t address) {
    if(!try_enter(address))throw std::runtime_error("KERNEL_CRITICAL_SECTION_CONTENTION_REQUIRES_SCHEDULER");
}
void CriticalSections::leave(std::uint32_t address) {
    auto state=lock_state(memory_,address);
    if(state.owner!=thread_ || !state.recursion)
        throw std::invalid_argument("KERNEL_CRITICAL_SECTION_NOT_OWNER");
    if(state.count!=state.recursion-1)
        throw std::runtime_error("KERNEL_CRITICAL_SECTION_WAITERS_REQUIRE_SCHEDULER");
    if(state.recursion==1)write_lock(memory_,address,{0xffffffff,0,0});
    else write_lock(memory_,address,{state.count-1,state.recursion-1,thread_});
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
