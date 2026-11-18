#include "kernel/tls_state.h"
#include <stdexcept>

namespace storm::kernel {
void map_thread_identity(memory::AddressSpace& memory,std::uint32_t pcr,
                         std::uint32_t thread,std::uint32_t id) {
    const auto pcr_end=std::uint64_t(pcr)+0x154,thread_end=std::uint64_t(thread)+0x150;
    if(!pcr || !thread || !id || pcr%4 || thread%4 || pcr_end>(UINT64_C(1)<<32) || thread_end>(UINT64_C(1)<<32))
        throw std::invalid_argument("KERNEL_THREAD_IDENTITY_LAYOUT");
    if((pcr<thread_end && thread<pcr_end) || !memory.available(pcr,0x154) || !memory.available(thread,0x150))
        throw std::invalid_argument("KERNEL_THREAD_IDENTITY_CONFLICT");
    const std::uint8_t pointer[]={std::uint8_t(thread>>24),std::uint8_t(thread>>16),std::uint8_t(thread>>8),std::uint8_t(thread)};
    const std::uint8_t number[]={std::uint8_t(id>>24),std::uint8_t(id>>16),std::uint8_t(id>>8),std::uint8_t(id)};
    memory.map(pcr+0x100,4,memory::Access::read,pointer,4);
    try{memory.map(thread+0x14c,4,memory::Access::read,number,4);}
    catch(...){memory.unmap(pcr+0x100);throw;}
}
DynamicTls::DynamicTls(memory::AddressSpace& memory,std::uint32_t slots):memory_(memory) {
    if(!slots || slots>2048)throw std::invalid_argument("KERNEL_TLS_SLOT_COUNT");
    allocated_.resize(slots,false);
}
void DynamicTls::attach(std::uint32_t thread,std::uint32_t base) {
    const auto size=allocated_.size()*4;
    if(!thread || thread%4 || !base || base%4 || std::uint64_t(base)+size>(UINT64_C(1)<<32))
        throw std::invalid_argument("KERNEL_TLS_THREAD_LAYOUT");
    if(threads_.count(thread))throw std::invalid_argument("KERNEL_TLS_THREAD_EXISTS");
    if(threads_.size()>=64)throw std::runtime_error("KERNEL_TLS_THREAD_LIMIT");
    if(!memory_.available(base,size))throw std::invalid_argument("KERNEL_TLS_REGION_CONFLICT");
    auto entry=threads_.emplace(thread,base);
    try{memory_.map(base,size,memory::Access::read_write);}
    catch(...){threads_.erase(entry.first);throw;}
}
std::uint32_t DynamicTls::address(std::uint32_t thread,std::uint32_t slot) const {
    const auto found=threads_.find(thread);
    if(found==threads_.end())throw std::invalid_argument("KERNEL_TLS_THREAD_NOT_BOUND");
    if(slot>=allocated_.size())throw std::invalid_argument("KERNEL_TLS_INDEX_RANGE");
    return found->second+slot*4;
}
std::uint32_t DynamicTls::allocate(std::uint32_t thread) {
    // Validate current thread even when no slots remain.
    address(thread,0);
    for(std::uint32_t slot=0;slot<allocated_.size();++slot)if(!allocated_[slot]) {
        memory_.store(address(thread,slot),4,0);
        allocated_[slot]=true;return slot;
    }
    return out_of_indexes;
}
bool DynamicTls::free(std::uint32_t slot) {
    if(slot>=allocated_.size() || !allocated_[slot])return false;
    // Validate all writes before clearing any thread or releasing the index.
    for(const auto& thread:threads_)memory_.require_access(thread.second+slot*4,4,memory::Access::read_write);
    for(const auto& thread:threads_)memory_.store(thread.second+slot*4,4,0);
    allocated_[slot]=false;return true;
}
std::uint32_t DynamicTls::get(std::uint32_t thread,std::uint32_t slot) const {
    const auto cell=address(thread,slot);
    if(!allocated_[slot])throw std::invalid_argument("KERNEL_TLS_INDEX_NOT_ALLOCATED");
    return std::uint32_t(memory_.load(cell,4));
}
void DynamicTls::set(std::uint32_t thread,std::uint32_t slot,std::uint32_t value) {
    const auto cell=address(thread,slot);
    if(!allocated_[slot])throw std::invalid_argument("KERNEL_TLS_INDEX_NOT_ALLOCATED");
    memory_.store(cell,4,value);
}
} // namespace storm::kernel
