#include "kernel/timestamp_bundle.h"
#include <array>
#include <cstring>
#include <stdexcept>
#include <utility>

namespace storm::kernel {
TimestampBundle::TimestampBundle(memory::AddressSpace& memory,std::uint32_t base,UptimeMillis clock)
    :memory_(memory),base_(base) {
    if(!clock || !base || base%4 || std::uint64_t(base)+24>(UINT64_C(1)<<32))
        throw std::invalid_argument("KERNEL_TIMESTAMP_LAYOUT");
    if(!memory.available(base,24))throw std::invalid_argument("KERNEL_TIMESTAMP_REGION_CONFLICT");
    memory.map_reader(base+16,4,[clock=std::move(clock)](std::size_t offset,std::uint8_t* out,std::size_t size){
        const auto value=std::uint32_t(clock());
        const std::array<std::uint8_t,4> bytes{std::uint8_t(value>>24),std::uint8_t(value>>16),std::uint8_t(value>>8),std::uint8_t(value)};
        std::memcpy(out,bytes.data()+offset,size);
    });
}
void TimestampBundle::bind_import(std::uint32_t slot,std::uint32_t expected) {
    if(!slot || slot%4 || expected>>24 || (expected&65535)!=0xad || memory_.load(slot,4)!=expected)
        throw std::invalid_argument("KERNEL_TIMESTAMP_IMPORT_MISMATCH");
    memory_.store(slot,4,base_);
}
} // namespace storm::kernel
