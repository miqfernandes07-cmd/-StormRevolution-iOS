#include "memory/address_space.h"
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <limits>
#include <string>
#include <utility>

namespace storm::memory {
namespace {
const char* label(MemoryFaultKind kind) {
    switch(kind) {
    case MemoryFaultKind::invalid_range:return "GUEST_ADDRESS_RANGE";
    case MemoryFaultKind::overlap:return "GUEST_REGION_OVERLAP";
    case MemoryFaultKind::unmapped:return "GUEST_ADDRESS_UNMAPPED";
    case MemoryFaultKind::read_only:return "GUEST_WRITE_READ_ONLY";
    case MemoryFaultKind::invalid_buffer:return "GUEST_COPY_BUFFER";
    case MemoryFaultKind::unsupported_atomic:return "GUEST_ATOMIC_UNSUPPORTED";
    }
    return "GUEST_MEMORY_FAULT";
}
std::string description(MemoryFaultKind kind,std::uint32_t address,std::size_t length) {
    char text[128];std::snprintf(text,sizeof(text),"%s: address=0x%08X length=%zu",label(kind),unsigned(address),length);return text;
}
}
MemoryFault::MemoryFault(MemoryFaultKind kind,std::uint32_t address,std::size_t length)
    :std::runtime_error(description(kind,address,length)),kind_(kind),address_(address),length_(length) {}
void AddressSpace::range(std::uint32_t address,std::size_t size) {
    if(size>(UINT64_C(1)<<32)-address)throw MemoryFault(MemoryFaultKind::invalid_range,address,size);
}
void AddressSpace::require_reservable(std::uint32_t address,bool write) const {
    if(address%4)throw MemoryFault(MemoryFaultKind::invalid_range,address,4);
    validate(address,4,write);
    for(std::uint64_t cursor=address;cursor<std::uint64_t(address)+4;++cursor)
        if(containing(std::uint32_t(cursor))->second.reader)
            throw MemoryFault(MemoryFaultKind::unsupported_atomic,address,4);
}
void AddressSpace::invalidate_reservations(std::uint32_t address,std::size_t size) {
    if(!size)return;
    const auto end=std::uint64_t(address)+size;
    auto first=reservation_versions_.lower_bound(address&~std::uint32_t(127));
    auto last=first;
    for(;last!=reservation_versions_.end()&&last->first<end;++last)
        if(last->second==UINT64_MAX)throw std::runtime_error("GUEST_RESERVATION_VERSION_EXHAUSTED");
    for(auto it=first;it!=last;++it)++it->second;
}
std::uint32_t AddressSpace::reserve_load32(std::uint32_t address,Reservation& reservation) {
    reservation.clear();require_reservable(address,false);
    const auto value=std::uint32_t(load(address,4));
    auto version=reservation_versions_.emplace(address&~std::uint32_t(127),0).first;
    reservation.owner_=this;reservation.address_=address;reservation.version_=version->second;
    return value;
}
bool AddressSpace::conditional_store32(std::uint32_t address,std::uint32_t value,Reservation& reservation) {
    const auto saved=reservation;reservation.clear();
    require_reservable(address,true);
    if(saved.owner_!=this || saved.address_!=address)return false;
    const auto version=reservation_versions_.find(address&~std::uint32_t(127));
    if(version==reservation_versions_.end() || version->second!=saved.version_)return false;
    store(address,4,value);return true;
}
void AddressSpace::map(std::uint32_t address,std::size_t size,Access access,const std::uint8_t* initial,std::size_t initial_size) {
    range(address,size);
    if(!size||size>1024ULL*1024*1024||(access!=Access::read&&access!=Access::read_write))
        throw MemoryFault(MemoryFaultKind::invalid_range,address,size);
    if(initial_size>size||(initial_size&&!initial))throw MemoryFault(MemoryFaultKind::invalid_buffer,address,initial_size);
    auto next=regions_.lower_bound(address);
    if(next!=regions_.end()&&std::uint64_t(address)+size>next->first)
        throw MemoryFault(MemoryFaultKind::overlap,address,size);
    if(next!=regions_.begin()) {
        const auto& prior=*std::prev(next);
        if(std::uint64_t(prior.first)+prior.second.bytes.size()>address)
            throw MemoryFault(MemoryFaultKind::overlap,address,size);
    }
    if(size>std::numeric_limits<std::size_t>::max()-mapped_bytes_)
        throw MemoryFault(MemoryFaultKind::invalid_range,address,size);
    Region region{access,std::vector<std::uint8_t>(size,0),{}};
    if(initial_size)std::memcpy(region.bytes.data(),initial,initial_size);
    auto inserted=regions_.emplace(address,std::move(region));
    try{invalidate_reservations(address,size);}
    catch(...){regions_.erase(inserted.first);throw;}
    mapped_bytes_+=size;
}
void AddressSpace::map_reader(std::uint32_t address,std::size_t size,ReadProvider reader) {
    if(!reader)throw MemoryFault(MemoryFaultKind::invalid_buffer,address,size);
    map(address,size,Access::read);
    regions_.find(address)->second.reader=std::move(reader);
}
void AddressSpace::require_access(std::uint32_t address,std::size_t size,Access access) const {
    if(access!=Access::read&&access!=Access::read_write)throw MemoryFault(MemoryFaultKind::invalid_range,address,size);
    validate(address,size,access==Access::read_write);
}
bool AddressSpace::available(std::uint32_t address,std::size_t size) const {
    range(address,size);if(!size)return false;
    auto next=regions_.lower_bound(address);
    if(next!=regions_.end()&&std::uint64_t(address)+size>next->first)return false;
    if(next!=regions_.begin()){const auto& prior=*std::prev(next);if(std::uint64_t(prior.first)+prior.second.bytes.size()>address)return false;}
    return true;
}
void AddressSpace::unmap(std::uint32_t start) {
    auto region=regions_.find(start);
    if(region==regions_.end())throw MemoryFault(MemoryFaultKind::unmapped,start,0);
    invalidate_reservations(start,region->second.bytes.size());
    mapped_bytes_-=region->second.bytes.size();regions_.erase(region);
}
AddressSpace::Regions::const_iterator AddressSpace::containing(std::uint32_t address) const {
    auto found=regions_.upper_bound(address);
    if(found==regions_.begin())return regions_.end();
    --found;
    if(std::uint64_t(address)-found->first>=found->second.bytes.size())return regions_.end();
    return found;
}
void AddressSpace::validate(std::uint32_t address,std::size_t size,bool write) const {
    range(address,size);std::uint64_t cursor=address;std::size_t remaining=size;
    while(remaining) {
        auto found=containing(std::uint32_t(cursor));
        if(found==regions_.end())throw MemoryFault(MemoryFaultKind::unmapped,std::uint32_t(cursor),remaining);
        if(write&&found->second.access!=Access::read_write)
            throw MemoryFault(MemoryFaultKind::read_only,std::uint32_t(cursor),remaining);
        const auto count=std::min(remaining,found->second.bytes.size()-std::size_t(cursor-found->first));
        cursor+=count;remaining-=count;
    }
}
void AddressSpace::copy_out(std::uint32_t address,void* destination,std::size_t size) const {
    if(size&&!destination)throw MemoryFault(MemoryFaultKind::invalid_buffer,address,size);
    validate(address,size,false);
    bool provided=false;
    std::uint64_t scan=address;std::size_t left=size;
    while(left) {
        auto region=containing(std::uint32_t(scan));
        provided=provided||bool(region->second.reader);
        const auto count=std::min(left,region->second.bytes.size()-std::size_t(scan-region->first));
        scan+=count;left-=count;
    }
    // A provider can fail. Sample into a temporary buffer before publishing any
    // bytes, including reads crossing static/provider region boundaries.
    std::vector<std::uint8_t> snapshot(provided?size:0);
    auto* bytes=provided?snapshot.data():static_cast<std::uint8_t*>(destination);
    std::uint64_t cursor=address;std::size_t remaining=size;
    while(remaining) {
        auto found=containing(std::uint32_t(cursor));const auto offset=std::size_t(cursor-found->first);
        const auto count=std::min(remaining,found->second.bytes.size()-offset);
        if(found->second.reader)found->second.reader(offset,bytes,count);
        else std::memcpy(bytes,found->second.bytes.data()+offset,count);
        bytes+=count;cursor+=count;remaining-=count;
    }
    if(provided&&size)std::memcpy(destination,snapshot.data(),size);
}
void AddressSpace::copy_in(std::uint32_t address,const void* source,std::size_t size) {
    if(size&&!source)throw MemoryFault(MemoryFaultKind::invalid_buffer,address,size);
    // Validate all spans first, so a permission/hole fault cannot partially write.
    validate(address,size,true);invalidate_reservations(address,size);const auto* bytes=static_cast<const std::uint8_t*>(source);
    std::uint64_t cursor=address;std::size_t remaining=size;
    while(remaining) {
        auto found=regions_.find(containing(std::uint32_t(cursor))->first);const auto offset=std::size_t(cursor-found->first);
        const auto count=std::min(remaining,found->second.bytes.size()-offset);
        std::memcpy(found->second.bytes.data()+offset,bytes,count);bytes+=count;cursor+=count;remaining-=count;
    }
}
std::uint64_t AddressSpace::load(std::uint32_t address,unsigned width) const {
    if(width!=1&&width!=2&&width!=4&&width!=8)throw MemoryFault(MemoryFaultKind::invalid_range,address,width);
    std::uint8_t bytes[8]{};copy_out(address,bytes,width);std::uint64_t value=0;
    for(unsigned i=0;i<width;i++)value=value<<8|bytes[i];
    return value;
}
void AddressSpace::store(std::uint32_t address,unsigned width,std::uint64_t value) {
    if(width!=1&&width!=2&&width!=4&&width!=8)throw MemoryFault(MemoryFaultKind::invalid_range,address,width);
    std::uint8_t bytes[8]{};
    for(unsigned i=0;i<width;i++)bytes[i]=std::uint8_t(value>>((width-1-i)*8));
    copy_in(address,bytes,width);
}
} // namespace storm::memory
