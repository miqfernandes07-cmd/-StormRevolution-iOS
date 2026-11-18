#include "memory/address_space.h"
#include "cpu/aot_dispatch.h"
#include <array>
#include <iostream>
#include <string>
struct PPCContext {unsigned tag;};
using namespace storm;
int main(){unsigned checks=0;
 auto check=[&](bool value){++checks;if(!value)throw std::runtime_error("reservation check "+std::to_string(checks));};
 auto fault=[&](auto action,memory::MemoryFaultKind kind){bool caught=false;try{action();}catch(const memory::MemoryFault& e){caught=e.kind()==kind;}check(caught);};
 try{
  memory::AddressSpace m;using R=memory::AddressSpace::Reservation;R a,b;
  m.map(0x10000,384,memory::Access::read_write);m.store(0x10000,4,0x12345678);
  check(!m.conditional_store32(0x10000,0,a));check(m.reserve_load32(0x10000,a)==0x12345678);
  check(m.conditional_store32(0x10000,0xaabbccdd,a));check(m.load(0x10000,1)==0xaa);
  check(!m.conditional_store32(0x10000,0,a));check(m.load(0x10000,4)==0xaabbccdd);
  m.reserve_load32(0x10000,a);m.store(0x10000,4,0xaabbccdd);check(!m.conditional_store32(0x10000,1,a));
  m.reserve_load32(0x10000,a);m.store(0x10000,4,1);m.store(0x10000,4,0xaabbccdd);check(!m.conditional_store32(0x10000,2,a));
  m.reserve_load32(0x10000,a);m.store(0x1007c,4,3);check(!m.conditional_store32(0x10000,2,a));
  m.reserve_load32(0x10000,a);m.store(0x10080,4,3);check(m.conditional_store32(0x10000,2,a));
  m.reserve_load32(0x10000,a);check(!m.conditional_store32(0x10004,4,a));check(!m.conditional_store32(0x10000,4,a));
  m.reserve_load32(0x10000,a);m.reserve_load32(0x10000,b);check(m.conditional_store32(0x10000,9,b));check(!m.conditional_store32(0x10000,10,a));
  m.reserve_load32(0x10000,a);std::array<std::uint8_t,8> bytes{};m.copy_in(0x10078,bytes.data(),bytes.size());check(!m.conditional_store32(0x10000,10,a));
  m.reserve_load32(0x10000,a);m.unmap(0x10000);m.map(0x10000,384,memory::Access::read_write);check(!m.conditional_store32(0x10000,10,a));
  m.reserve_load32(0x10000,a);fault([&]{m.reserve_load32(0x10001,a);},memory::MemoryFaultKind::invalid_range);check(!m.conditional_store32(0x10000,10,a));
  m.reserve_load32(0x10000,a);fault([&]{m.conditional_store32(0x10001,10,a);},memory::MemoryFaultKind::invalid_range);check(!m.conditional_store32(0x10000,10,a));
  memory::AddressSpace other;other.map(0x10000,4,memory::Access::read_write);
  m.reserve_load32(0x10000,a);check(!other.conditional_store32(0x10000,10,a));
  memory::AddressSpace partial;partial.map(0x20000,4,memory::Access::read_write);partial.reserve_load32(0x20000,a);
  partial.map(0x20004,4,memory::Access::read);check(!partial.conditional_store32(0x20000,10,a));
  m.map(0x20000,4,memory::Access::read);m.reserve_load32(0x20000,a);
  fault([&]{m.conditional_store32(0x20000,1,a);},memory::MemoryFaultKind::read_only);
  unsigned sampled=0;m.map_reader(0x30000,4,[&](auto,auto*,auto){++sampled;});
  fault([&]{m.reserve_load32(0x30000,a);},memory::MemoryFaultKind::unsupported_atomic);check(sampled==0);
  memory::AddressSpace edge;edge.map(0xfffffffc,4,memory::Access::read_write);edge.reserve_load32(0xfffffffc,a);check(edge.conditional_store32(0xfffffffc,0xabcdef01,a));check(edge.load(0xfffffffc,4)==0xabcdef01);
  // Binding-local reservations are independent, but writes invalidate shared guest granules.
  cpu::AotFunctionTable table;table.seal();PPCContext first{},second{};std::uint8_t base_a[1]{},base_b[1]{};
  bool caught=false;try{cpu::load_reserve_guest32(first,base_a,0x10000);}catch(const cpu::DispatchFault& e){caught=e.kind()==cpu::DispatchFaultKind::unbound_thread;}check(caught);
  {cpu::AotBinding bind(table,first,base_a,&m);
   cpu::load_reserve_guest32(first,base_a,0x10000);
   {cpu::AotBinding nested(table,second,base_b,&m);cpu::load_reserve_guest32(second,base_b,0x10000);check(cpu::store_conditional_guest32(second,base_b,0x10000,99));}
   check(!cpu::store_conditional_guest32(first,base_a,0x10000,100));
   cpu::load_reserve_guest32(first,base_a,0x10000);
   {cpu::AotBinding nested(table,second,base_b,&m);}
   check(cpu::store_conditional_guest32(first,base_a,0x10000,101));
  }
  {cpu::AotBinding fresh(table,first,base_a,&m);check(!cpu::store_conditional_guest32(first,base_a,0x10000,102));}
  std::cout<<"reservations: "<<checks<<" checks passed; serialized guest32 model only\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
