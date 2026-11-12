#include "kernel/virtual_memory.h"
#include <algorithm>
#include <new>
#include <stdexcept>
#include <vector>

namespace storm::kernel {
namespace {
constexpr std::uint32_t commit=0x1000,reserve=0x2000,release=0x8000,
    top_down=0x100000,large_pages=0x20000000,heap=0x40000000;
constexpr std::uint64_t budget=512ULL*1024*1024;
std::uint64_t align_up(std::uint64_t value,std::uint32_t page){return (value+page-1)&~std::uint64_t(page-1);}
}
bool VirtualMemory::available(std::uint32_t base,std::uint32_t size) const {
    if(!space_.available(base,size))return false;
    auto next=allocations_.lower_bound(base);
    if(next!=allocations_.end()&&std::uint64_t(base)+size>next->first)return false;
    if(next!=allocations_.begin()){auto prior=std::prev(next);if(std::uint64_t(prior->first)+prior->second.size>base)return false;}
    return true;
}
std::uint32_t VirtualMemory::allocate(std::uint32_t& base,std::uint32_t& size,std::uint32_t flags,std::uint32_t protection,std::uint32_t debug) {
    if(!size||!(flags&(commit|reserve)))return invalid_parameter;
    if(debug||flags&~(commit|reserve|top_down|large_pages|heap))throw std::runtime_error("KERNEL_VM_ALLOCATION_MODE_UNIMPLEMENTED");
    if(protection!=2&&protection!=4)throw std::runtime_error("KERNEL_VM_PROTECTION_UNIMPLEMENTED");
    const auto access=protection==4?memory::Access::read_write:memory::Access::read;
    const std::uint32_t page=base?(base<0x40000000?4096:65536):(flags&large_pages?65536:4096);
    const std::uint32_t lower=page==4096?0x10000:0x40000000;
    const std::uint64_t upper=page==4096?0x40000000:0x7f000000;
    const std::uint64_t raw_size=(size&0x80000000u)?std::uint32_t(0u-size):size;
    const auto rounded=align_up(raw_size,page);
    if(!rounded||rounded>upper-lower)return no_memory;
    std::uint32_t address=base&~(page-1);const auto amount=std::uint32_t(rounded);
    if(address&&(address<lower||std::uint64_t(address)+amount>upper))return conflicting_addresses;
    bool created=false;auto allocation=allocations_.end();
    if(address&&!(flags&reserve)) {
        allocation=allocations_.upper_bound(address);
        if(allocation==allocations_.begin())return conflicting_addresses;
        --allocation;
        if(std::uint64_t(address)+amount>std::uint64_t(allocation->first)+allocation->second.size)return conflicting_addresses;
    }else {
        if(!address) {
            // Conservative bounded first fit. Large occupied reservations are
            // skipped in one step; external byte regions remain authoritative.
            if(flags&top_down) {
                std::uint64_t candidate=(upper-amount)&~std::uint64_t(page-1);
                while(candidate>=lower) {
                    if(available(std::uint32_t(candidate),amount)){address=std::uint32_t(candidate);break;}
                    if(candidate<lower+page)break;
                    candidate-=page;
                }
            }else {
                std::uint64_t candidate=lower;
                while(candidate+amount<=upper) {
                    if(available(std::uint32_t(candidate),amount)){address=std::uint32_t(candidate);break;}
                    auto next=allocations_.upper_bound(std::uint32_t(candidate));
                    if(next!=allocations_.begin()){auto prior=std::prev(next);if(candidate<std::uint64_t(prior->first)+prior->second.size){candidate=align_up(std::uint64_t(prior->first)+prior->second.size,page);continue;}}
                    candidate+=page;
                }
            }
            if(!address)return no_memory;
        }else if(!available(address,amount))return conflicting_addresses;
        try{allocation=allocations_.emplace(address,Allocation{amount,page,{}}).first;created=true;}
        catch(const std::bad_alloc&){return no_memory;}
    }
    auto& record=allocation->second;
    std::vector<std::uint32_t> added;
    try {
        if(flags&commit) {
            std::size_t needed=0;
            for(std::uint64_t current=address;current<std::uint64_t(address)+amount;current+=page) {
                auto existing=record.committed.find(std::uint32_t(current));
                if(existing==record.committed.end())needed+=page;
                else if(existing->second!=access)throw std::runtime_error("KERNEL_VM_RECOMMIT_PROTECTION_UNIMPLEMENTED");
            }
            if(needed>budget-committed_bytes_){if(created)allocations_.erase(allocation);return no_memory;}
            added.reserve(needed/page);
            for(std::uint64_t current=address;current<std::uint64_t(address)+amount;current+=page) {
                auto guest=std::uint32_t(current);if(record.committed.find(guest)!=record.committed.end())continue;
                space_.map(guest,page,access);
                try{record.committed.emplace(guest,access);}catch(...){space_.unmap(guest);throw;}
                added.push_back(guest);
            }
            committed_bytes_+=needed;
        }
    }catch(...) {
        for(auto guest:added){space_.unmap(guest);record.committed.erase(guest);}
        if(created)allocations_.erase(allocation);
        try{throw;}catch(const std::bad_alloc&){return no_memory;}
    }
    base=address;size=amount;return success;
}
std::uint32_t VirtualMemory::free(std::uint32_t& base,std::uint32_t& size,std::uint32_t flags) {
    if(flags!=release)throw std::runtime_error("KERNEL_VM_FREE_MODE_UNIMPLEMENTED");
    if(size)return invalid_parameter;
    auto allocation=allocations_.find(base);
    if(allocation==allocations_.end())return invalid_parameter;
    for(const auto& entry:allocation->second.committed){space_.unmap(entry.first);committed_bytes_-=allocation->second.page;}
    allocations_.erase(allocation);base=0;size=0;return success;
}
std::uint32_t VirtualMemory::allocate_guest(std::uint32_t base_pointer,std::uint32_t size_pointer,std::uint32_t flags,std::uint32_t protection,std::uint32_t debug) {
    if(!base_pointer||!size_pointer)return invalid_parameter;
    space_.require_access(base_pointer,4,memory::Access::read_write);
    space_.require_access(size_pointer,4,memory::Access::read_write);
    auto base=std::uint32_t(space_.load(base_pointer,4)),size=std::uint32_t(space_.load(size_pointer,4));
    const auto status=allocate(base,size,flags,protection,debug);
    if(status==success){space_.store(base_pointer,4,base);space_.store(size_pointer,4,size);}
    return status;
}
std::uint32_t VirtualMemory::free_guest(std::uint32_t base_pointer,std::uint32_t size_pointer,std::uint32_t flags) {
    if(!base_pointer||!size_pointer)return invalid_parameter;
    space_.require_access(base_pointer,4,memory::Access::read_write);
    space_.require_access(size_pointer,4,memory::Access::read_write);
    auto base=std::uint32_t(space_.load(base_pointer,4)),size=std::uint32_t(space_.load(size_pointer,4));
    auto allocation=allocations_.find(base);
    if(allocation!=allocations_.end()) {
        const auto end=std::uint64_t(base)+allocation->second.size;
        for(auto pointer:{base_pointer,size_pointer})
            if(std::uint64_t(pointer)<end&&std::uint64_t(pointer)+4>base)
                throw std::runtime_error("KERNEL_VM_OUTPUT_IN_RELEASED_REGION_UNIMPLEMENTED");
    }
    const auto status=free(base,size,flags);
    if(status==success){space_.store(base_pointer,4,base);space_.store(size_pointer,4,size);}
    return status;
}
} // namespace storm::kernel
