#include "kernel/process_state.h"
#include <array>
#include <iostream>
#include <string>

int main(){using namespace storm;unsigned checks=0;
 auto check=[&](bool value){++checks;if(!value)throw std::runtime_error("process check "+std::to_string(checks));};
 auto invalid=[&](auto action,const char* code){bool caught=false;try{action();}catch(const std::invalid_argument& e){caught=std::string(e.what())==code;}check(caught);};
 try{
  memory::AddressSpace space;kernel::ProcessState process(space,0x80010000);
  check(space.mapped_bytes()==1);check(process.get_type()==1);
  for(unsigned value=0;value<3;++value){process.set_type(value);check(process.get_type()==value);check(space.load(0x8001002f,1)==value);}
  space.store(0x8001002f,1,255);check(process.get_type()==255);
  invalid([&]{process.set_type(3);},"KERNEL_PROCESS_TYPE_INVALID");check(process.get_type()==255);
  invalid([&]{process.set_type(0xffffffff);},"KERNEL_PROCESS_TYPE_INVALID");check(process.get_type()==255);
  for(auto address:{0u,3u,0xffffffa4u})invalid([&]{kernel::ProcessState bad(space,address);},"KERNEL_PROCESS_LAYOUT_INVALID");
  bool fault=false;try{space.load(0x80010000,1);}catch(const memory::MemoryFault&){fault=true;}check(fault);
  invalid([&]{kernel::ProcessState duplicate(space,0x80010000);},"KERNEL_PROCESS_REGION_CONFLICT");check(space.mapped_bytes()==1);
  memory::AddressSpace occupied;occupied.map(0x40000,4,memory::Access::read_write);
  invalid([&]{kernel::ProcessState overlapping(occupied,0x40000);},"KERNEL_PROCESS_REGION_CONFLICT");check(occupied.mapped_bytes()==4);
  struct Case{std::uint32_t spin;unsigned units;};
  for(auto c:std::array<Case,9>{{{0,0},{1,1},{255,1},{256,1},{257,2},{65280,255},{65536,255},{0xffffff00,255},{0xffffffff,0}}}){
   memory::AddressSpace cs;std::array<std::uint8_t,28> bytes;bytes.fill(0xa5);cs.map(0x10000,28,memory::Access::read_write,bytes.data(),bytes.size());
   check(kernel::initialize_critical_section(cs,0x10000,c.spin)==0);
   std::array<std::uint8_t,28> actual;cs.copy_out(0x10000,actual.data(),actual.size());
   auto expected=bytes;expected[0]=1;expected[1]=c.units;
   for(unsigned i=4;i<8;++i)expected[i]=0;
   for(unsigned i=16;i<20;++i)expected[i]=255;
   for(unsigned i=20;i<28;++i)expected[i]=0;
   check(actual==expected);
  }
  // Every possible missing/read-only written byte must reject before mutation.
  for(unsigned gap=0;gap<28;++gap){if(gap==2||gap==3||(gap>=8&&gap<16))continue;
   for(bool read_only:{false,true}){
    memory::AddressSpace cs;std::array<std::uint8_t,28> original;original.fill(0x5a);
    if(gap)cs.map(0x20000,gap,memory::Access::read_write,original.data(),gap);
    if(read_only)cs.map(0x20000+gap,1,memory::Access::read,original.data()+gap,1);
    if(gap<27)cs.map(0x20001+gap,27-gap,memory::Access::read_write,original.data()+gap+1,27-gap);
    fault=false;try{kernel::initialize_critical_section(cs,0x20000);}catch(const memory::MemoryFault&){fault=true;}check(fault);
    for(unsigned i=0;i<28;++i)if(i!=gap||read_only)check(cs.load(0x20000+i,1)==0x5a);
   }
  }
  memory::AddressSpace sparse;sparse.map(0x30000,2,memory::Access::read_write);sparse.map(0x30004,4,memory::Access::read_write);sparse.map(0x30010,12,memory::Access::read_write);
  check(kernel::initialize_critical_section(sparse,0x30000)==0);check(sparse.load(0x30010,4)==0xffffffff);
  invalid([&]{kernel::initialize_critical_section(sparse,0);},"KERNEL_CRITICAL_SECTION_RANGE");
  invalid([&]{kernel::initialize_critical_section(sparse,0xfffffff0);},"KERNEL_CRITICAL_SECTION_RANGE");
  std::cout<<"process/critical initialization: "<<checks<<" checks passed; no scheduler or game boot\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
