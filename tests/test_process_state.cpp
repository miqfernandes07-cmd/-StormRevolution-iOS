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
  memory::AddressSpace hardware_space;
  kernel::HardwareInfo hardware(hardware_space,0x50000,0x12345678,6);
  check(hardware_space.load(0x50000,4)==0x12345678);
  check(hardware_space.load(0x50004,1)==6);check(hardware_space.mapped_bytes()==5);
  fault=false;try{hardware_space.load(0x50005,1);}catch(const memory::MemoryFault&){fault=true;}check(fault);
  fault=false;try{hardware_space.store(0x50000,4,0);}catch(const memory::MemoryFault&){fault=true;}check(fault);
  for(auto address:{0u,3u,0xfffffff4u})invalid([&]{kernel::HardwareInfo bad(hardware_space,address,0,6);},"KERNEL_HARDWARE_LAYOUT_INVALID");
  for(auto cpus:{0u,7u})invalid([&]{kernel::HardwareInfo bad(hardware_space,0x60000,0,cpus);},"KERNEL_HARDWARE_LAYOUT_INVALID");
  invalid([&]{kernel::HardwareInfo bad(hardware_space,0x50000,0,6);},"KERNEL_HARDWARE_REGION_CONFLICT");
  hardware_space.map(0x60000,4,memory::Access::read_write);hardware_space.store(0x60000,4,0x10156);
  invalid([&]{hardware.bind_import(0x60000,0x10193);},"KERNEL_HARDWARE_IMPORT_MISMATCH");
  invalid([&]{hardware.bind_import(0x60000,0x1000156);},"KERNEL_HARDWARE_IMPORT_MISMATCH");
  invalid([&]{hardware.bind_import(0x60001,0x10156);},"KERNEL_HARDWARE_IMPORT_MISMATCH");
  check(hardware_space.load(0x60000,4)==0x10156);
  hardware.bind_import(0x60000,0x10156);check(hardware_space.load(0x60000,4)==0x50000);
  invalid([&]{hardware.bind_import(0x60000,0x10156);},"KERNEL_HARDWARE_IMPORT_MISMATCH");
  hardware_space.map(0x70000,4,memory::Access::read, std::array<std::uint8_t,4>{0,1,1,0x56}.data(),4);
  fault=false;try{hardware.bind_import(0x70000,0x10156);}catch(const memory::MemoryFault&){fault=true;}check(fault);
  check(hardware_space.load(0x70000,4)==0x10156);
  memory::AddressSpace conflict;conflict.map(0x8000f,1,memory::Access::read_write);
  invalid([&]{kernel::HardwareInfo bad(conflict,0x80000,0x20,6);},"KERNEL_HARDWARE_REGION_CONFLICT");
  check(conflict.mapped_bytes()==1);
  memory::AddressSpace locks_memory;std::array<std::uint8_t,28> lock_bytes;lock_bytes.fill(0xa5);
  locks_memory.map(0x90000,28,memory::Access::read_write,lock_bytes.data(),lock_bytes.size());
  kernel::initialize_critical_section(locks_memory,0x90000,1024);
  kernel::CriticalSections first(locks_memory,0x1000),second(locks_memory,0x2000);
  auto lock_snapshot=[&]{std::array<std::uint8_t,28> bytes;locks_memory.copy_out(0x90000,bytes.data(),bytes.size());return bytes;};
  auto lock_failure=[&](auto action,const char* code){auto before=lock_snapshot();bool caught=false;try{action();}catch(const std::exception& e){caught=std::string(e.what())==code;}check(caught);check(lock_snapshot()==before);};
  invalid([&]{kernel::CriticalSections bad(locks_memory,0);},"KERNEL_THREAD_IDENTITY_REQUIRED");
  invalid([&]{kernel::CriticalSections bad(locks_memory,3);},"KERNEL_THREAD_IDENTITY_REQUIRED");
  for(unsigned iteration=0;iteration<100;++iteration){
   auto before=lock_snapshot();first.enter(0x90000);
   check(locks_memory.load(0x90010,4)==0);check(locks_memory.load(0x90014,4)==1);check(locks_memory.load(0x90018,4)==0x1000);
   first.enter(0x90000);check(first.try_enter(0x90000));
   check(locks_memory.load(0x90010,4)==2);check(locks_memory.load(0x90014,4)==3);
   auto held=lock_snapshot();check(!second.try_enter(0x90000));check(held==lock_snapshot());
   lock_failure([&]{second.enter(0x90000);},"KERNEL_CRITICAL_SECTION_CONTENTION_REQUIRES_SCHEDULER");
   lock_failure([&]{second.leave(0x90000);},"KERNEL_CRITICAL_SECTION_NOT_OWNER");
   first.leave(0x90000);first.leave(0x90000);first.leave(0x90000);check(before==lock_snapshot());
   check(second.try_enter(0x90000));check(locks_memory.load(0x90018,4)==0x2000);second.leave(0x90000);
   check(before==lock_snapshot());
  }
  lock_failure([&]{first.leave(0x90000);},"KERNEL_CRITICAL_SECTION_NOT_OWNER");
  locks_memory.store(0x90000,1,0);lock_failure([&]{first.enter(0x90000);},"KERNEL_CRITICAL_SECTION_TYPE");locks_memory.store(0x90000,1,1);
  locks_memory.store(0x90010,4,0);lock_failure([&]{first.enter(0x90000);},"KERNEL_CRITICAL_SECTION_STATE");
  locks_memory.store(0x90014,4,1);locks_memory.store(0x90018,4,0x1000);locks_memory.store(0x90010,4,1);
  lock_failure([&]{first.enter(0x90000);},"KERNEL_CRITICAL_SECTION_WAITERS_REQUIRE_SCHEDULER");
  lock_failure([&]{first.leave(0x90000);},"KERNEL_CRITICAL_SECTION_WAITERS_REQUIRE_SCHEDULER");
  locks_memory.store(0x90014,4,0x7fffffff);locks_memory.store(0x90010,4,0x7ffffffe);
  lock_failure([&]{first.enter(0x90000);},"KERNEL_CRITICAL_SECTION_RECURSION_LIMIT");
  // Missing/read-only destination bytes must not leave partial lock mutations.
  for(unsigned gap=16;gap<28;++gap)for(bool read_only:{false,true}){
   memory::AddressSpace partial;std::array<std::uint8_t,28> initial{};initial[0]=1;
   for(unsigned i=16;i<20;++i)initial[i]=255;
   partial.map(0xa0000,gap,memory::Access::read_write,initial.data(),gap);
   if(read_only)partial.map(0xa0000+gap,1,memory::Access::read,initial.data()+gap,1);
   if(gap<27)partial.map(0xa0001+gap,27-gap,memory::Access::read_write,initial.data()+gap+1,27-gap);
   kernel::CriticalSections partial_lock(partial,0x1000);
   fault=false;try{partial_lock.enter(0xa0000);}catch(const memory::MemoryFault&){fault=true;}check(fault);
   for(unsigned i=0;i<28;++i)if(i!=gap||read_only)check(partial.load(0xa0000+i,1)==initial[i]);
  }
  std::cout<<"process/critical initialization: "<<checks<<" checks passed; no scheduler or game boot\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
