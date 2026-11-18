#include "kernel/timestamp_bundle.h"
#include <array>
#include <iostream>
#include <string>
using namespace storm;
int main(){unsigned checks=0;
 auto check=[&](bool value){++checks;if(!value)throw std::runtime_error("timestamp check "+std::to_string(checks));};
 auto invalid=[&](auto action,const char* code){bool caught=false;try{action();}catch(const std::invalid_argument& e){caught=std::string(e.what())==code;}check(caught);};
 auto fault=[&](auto action){bool caught=false;try{action();}catch(const memory::MemoryFault&){caught=true;}check(caught);};
 try{
  memory::AddressSpace memory;std::uint64_t millis=0;unsigned samples=0;
  kernel::TimestampBundle bundle(memory,0x10000,[&]{++samples;return millis;});
  check(memory.mapped_bytes()==4);check(memory.load(0x10010,4)==0);check(samples==1);
  millis=1234;check(memory.load(0x10010,4)==1234);check(samples==2);
  millis=0x12345678;check(memory.load(0x10010,1)==0x12);check(memory.load(0x10011,2)==0x3456);check(memory.load(0x10013,1)==0x78);
  millis=UINT64_C(0x100000003);check(memory.load(0x10010,4)==3);
  fault([&]{memory.load(0x10000,8);});fault([&]{memory.load(0x10014,4);});
  fault([&]{memory.store(0x10010,4,0);});check(memory.load(0x10010,4)==3);
  memory.map(0x20000,4,memory::Access::read_write);memory.store(0x20000,4,0x100ad);
  invalid([&]{bundle.bind_import(0x20000,0x100ae);},"KERNEL_TIMESTAMP_IMPORT_MISMATCH");
  invalid([&]{bundle.bind_import(0x20001,0x100ad);},"KERNEL_TIMESTAMP_IMPORT_MISMATCH");
  invalid([&]{bundle.bind_import(0x20000,0x10000ad);},"KERNEL_TIMESTAMP_IMPORT_MISMATCH");
  check(memory.load(0x20000,4)==0x100ad);bundle.bind_import(0x20000,0x100ad);check(memory.load(0x20000,4)==0x10000);
  invalid([&]{bundle.bind_import(0x20000,0x100ad);},"KERNEL_TIMESTAMP_IMPORT_MISMATCH");
  for(auto address:{0u,3u,0xffffffecu})invalid([&]{kernel::TimestampBundle bad(memory,address,[]{return 0;});},"KERNEL_TIMESTAMP_LAYOUT");
  invalid([&]{kernel::TimestampBundle bad(memory,0x30000,{});},"KERNEL_TIMESTAMP_LAYOUT");
  memory.map(0x30017,1,memory::Access::read);
  invalid([&]{kernel::TimestampBundle bad(memory,0x30000,[]{return 0;});},"KERNEL_TIMESTAMP_REGION_CONFLICT");
  fault([&]{memory.load(0x30010,4);});
  {
   kernel::TimestampBundle temporary(memory,0x40000,[]{return UINT64_C(0xabcdef);});
  }
  check(memory.load(0x40010,4)==0xabcdef); // callback lifetime belongs to the region
  memory::AddressSpace edge;kernel::TimestampBundle top(edge,0xffffffe8,[]{return 42;});
  check(edge.load(0xfffffff8,4)==42);
  std::cout<<"timestamp bundle: "<<checks<<" checks passed; sampled uptime field only\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
