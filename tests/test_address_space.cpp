#include "memory/address_space.h"
#include <array>
#include <cstring>
#include <iostream>
#include <string>
using namespace storm::memory;
int main() {
    unsigned checks=0;
    auto check=[&](bool condition){++checks;if(!condition)throw std::runtime_error("address-space check "+std::to_string(checks));};
    auto fault=[&](auto action,MemoryFaultKind expected,std::uint32_t address){
        bool caught=false;try{action();}catch(const MemoryFault& error){caught=error.kind()==expected&&error.address()==address&&std::string(error.what()).find("address=0x")!=std::string::npos;}check(caught);
    };
    try {
        AddressSpace space;
        const std::array<std::uint8_t,4> data{0x12,0x34,0x56,0x78};
        space.map(0x82000000,16,Access::read,data.data(),data.size());
        space.map(0x70000000,8,Access::read_write);space.map(0x70000008,8,Access::read_write);
        space.map(0xfffffff8,8,Access::read_write);
        check(space.mapped_bytes()==40);
        check(space.load(0x82000000,4)==0x12345678);check(space.load(0x82000004,8)==0);
        space.store(0x70000005,8,UINT64_C(0x0123456789abcdef));
        check(space.load(0x70000005,8)==UINT64_C(0x0123456789abcdef));
        check(space.load(0x70000007,2)==0x4567);check(space.load(0x7000000c,1)==0xef);
        space.store(0xfffffff8,8,UINT64_MAX);check(space.load(0xffffffff,1)==255);
        fault([&]{space.store(0x82000000,4,0);},MemoryFaultKind::read_only,0x82000000);
        check(space.load(0x82000000,4)==0x12345678);
        fault([&]{space.load(0xfffffffc,8);},MemoryFaultKind::invalid_range,0xfffffffc);
        fault([&]{space.load(0x1000,1);},MemoryFaultKind::unmapped,0x1000);
        fault([&]{space.load(0,1);},MemoryFaultKind::unmapped,0);
        fault([&]{space.map(0xfffffff0,32,Access::read_write);},MemoryFaultKind::invalid_range,0xfffffff0);
        fault([&]{space.map(0x70000007,2,Access::read_write);},MemoryFaultKind::overlap,0x70000007);
        fault([&]{space.map(0x6ffffff0,17,Access::read_write);},MemoryFaultKind::overlap,0x6ffffff0);
        fault([&]{space.map(0x70000000,8,Access::read_write);},MemoryFaultKind::overlap,0x70000000);
        fault([&]{space.map(0x1000,0,Access::read);},MemoryFaultKind::invalid_range,0x1000);
        fault([&]{space.map(0x1000,1024ULL*1024*1024+1,Access::read);},MemoryFaultKind::invalid_range,0x1000);
        fault([&]{space.map(0x1000,4,Access::read,nullptr,1);},MemoryFaultKind::invalid_buffer,0x1000);
        fault([&]{space.map(0x1000,2,Access::read,data.data(),4);},MemoryFaultKind::invalid_buffer,0x1000);
        fault([&]{space.map(0x1000,4,static_cast<Access>(2));},MemoryFaultKind::invalid_range,0x1000);
        fault([&]{space.copy_in(0x70000000,nullptr,1);},MemoryFaultKind::invalid_buffer,0x70000000);
        fault([&]{space.copy_out(0x70000000,nullptr,1);},MemoryFaultKind::invalid_buffer,0x70000000);
        space.copy_in(0,nullptr,0);space.copy_out(0,nullptr,0);check(true);
        for(unsigned width:{0u,3u,9u}){
            fault([&]{space.load(0x70000000,width);},MemoryFaultKind::invalid_range,0x70000000);
            fault([&]{space.store(0x70000000,width,0);},MemoryFaultKind::invalid_range,0x70000000);
        }
        std::array<std::uint8_t,12> original{};space.copy_out(0x70000004,original.data(),12);
        std::array<std::uint8_t,16> replacement{};replacement.fill(255);
        fault([&]{space.copy_in(0x70000004,replacement.data(),16);},MemoryFaultKind::unmapped,0x70000010);
        std::array<std::uint8_t,12> after{};space.copy_out(0x70000004,after.data(),12);check(after==original);
        space.map(0x70000010,4,Access::read);
        fault([&]{space.copy_in(0x70000004,replacement.data(),16);},MemoryFaultKind::read_only,0x70000010);
        space.copy_out(0x70000004,after.data(),12);check(after==original);
        std::array<std::uint8_t,16> dest{};dest.fill(99);
        fault([&]{space.copy_out(0x7000000c,dest.data(),16);},MemoryFaultKind::unmapped,0x70000014);
        bool unchanged=true;for(auto value:dest)unchanged=unchanged&&value==99;check(unchanged);
        space.unmap(0x70000008);check(space.mapped_bytes()==36);
        fault([&]{space.load(0x70000007,2);},MemoryFaultKind::unmapped,0x70000008);
        fault([&]{space.unmap(0x70000008);},MemoryFaultKind::unmapped,0x70000008);
        space.map(0x70000008,8,Access::read_write);check(space.load(0x70000008,8)==0);
        std::uint64_t seed=19;
        for(unsigned width:{1u,2u,4u,8u})for(unsigned i=0;i<512;i++){
            seed=seed*UINT64_C(6364136223846793005)+1;space.store(0x70000007,width,seed);
            const auto mask=width==8?UINT64_MAX:((UINT64_C(1)<<(width*8))-1);
            check(space.load(0x70000007,width)==(seed&mask));
        }
        std::cout<<"address space: "<<checks<<" checks passed; sparse guest regions, no MMIO\n";
        return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
