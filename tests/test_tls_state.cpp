#include "kernel/tls_state.h"
#include <array>
#include <iostream>
#include <string>
using namespace storm;
int main(){unsigned checks=0;
 auto check=[&](bool value){++checks;if(!value)throw std::runtime_error("TLS check "+std::to_string(checks));};
 auto invalid=[&](auto action,const char* code){bool caught=false;try{action();}catch(const std::invalid_argument& e){caught=std::string(e.what())==code;}check(caught);};
 auto fault=[&](auto action){bool caught=false;try{action();}catch(const memory::MemoryFault&){caught=true;}check(caught);};
 try{
  memory::AddressSpace space;
  for(auto size:{0u,2049u,0xffffffffu})invalid([&]{kernel::DynamicTls bad(space,size);},"KERNEL_TLS_SLOT_COUNT");
  kernel::DynamicTls tls(space,64);
  invalid([&]{tls.allocate(0x1000);},"KERNEL_TLS_THREAD_NOT_BOUND");
  for(auto layout:std::array<std::array<std::uint32_t,2>,5>{{{0,0x10000},{3,0x10000},{0x1000,0},{0x1000,3},{0x1000,0xffffff04}}})
   invalid([&]{tls.attach(layout[0],layout[1]);},"KERNEL_TLS_THREAD_LAYOUT");
  tls.attach(0x1000,0x10000);tls.attach(0x2000,0x20000);
  invalid([&]{tls.attach(0x1000,0x30000);},"KERNEL_TLS_THREAD_EXISTS");
  invalid([&]{tls.attach(0x3000,0x10000);},"KERNEL_TLS_REGION_CONFLICT");
  check(space.mapped_bytes()==512);
  for(unsigned i=0;i<64;++i){
   check(tls.allocate(0x1000)==i);check(tls.get(0x1000,i)==0);check(tls.get(0x2000,i)==0);
   tls.set(0x1000,i,0x12340000+i);tls.set(0x2000,i,0xabcdef00+i);
   check(space.load(0x10000+i*4,1)==0x12);
   check(tls.get(0x1000,i)==0x12340000+i);check(tls.get(0x2000,i)==0xabcdef00+i);
  }
  check(tls.allocate(0x1000)==kernel::DynamicTls::out_of_indexes);
  check(tls.allocate(0x2000)==kernel::DynamicTls::out_of_indexes);
  for(auto index:{64u,0xffffffffu}){
   invalid([&]{tls.get(0x1000,index);},"KERNEL_TLS_INDEX_RANGE");
   invalid([&]{tls.set(0x1000,index,1);},"KERNEL_TLS_INDEX_RANGE");check(!tls.free(index));
  }
  invalid([&]{tls.set(0x3000,0,1);},"KERNEL_TLS_THREAD_NOT_BOUND");
  tls.attach(0x3000,0x30000);check(tls.get(0x3000,20)==0);
  space.store(0x30000+20*4,4,0xffffffff);check(tls.get(0x3000,20)==0xffffffff);
  check(tls.free(20));check(!tls.free(20));
  for(auto thread:{0x1000u,0x2000u,0x3000u})invalid([&]{tls.get(thread,20);},"KERNEL_TLS_INDEX_NOT_ALLOCATED");
  check(tls.allocate(0x2000)==20);
  for(auto thread:{0x1000u,0x2000u,0x3000u})check(tls.get(thread,20)==0);
  // Allocation must not consume a slot when its guest write fails.
  memory::AddressSpace broken;kernel::DynamicTls transactional(broken,2);transactional.attach(0x1000,0x40000);
  broken.unmap(0x40000);broken.map(0x40000,8,memory::Access::read);
  fault([&]{transactional.allocate(0x1000);});
  broken.unmap(0x40000);broken.map(0x40000,8,memory::Access::read_write);
  check(transactional.allocate(0x1000)==0);transactional.set(0x1000,0,0x11223344);
  transactional.attach(0x2000,0x50000);transactional.set(0x2000,0,0xaabbccdd);
  broken.unmap(0x50000);const std::array<std::uint8_t,4> saved{0xaa,0xbb,0xcc,0xdd};
  broken.map(0x50000,4,memory::Access::read,saved.data(),saved.size());
  fault([&]{transactional.free(0);});check(transactional.get(0x1000,0)==0x11223344);check(transactional.get(0x2000,0)==0xaabbccdd);
  check(transactional.allocate(0x1000)==1);
  broken.unmap(0x50000);broken.map(0x50000,8,memory::Access::read_write);
  check(transactional.free(0));check(transactional.allocate(0x1000)==0);
  check(transactional.get(0x1000,0)==0);check(transactional.get(0x2000,0)==0);
  kernel::DynamicTls independent(broken,1);independent.attach(0x1000,0x60000);check(independent.allocate(0x1000)==0);
  memory::AddressSpace edge;kernel::DynamicTls at_end(edge,64);at_end.attach(4,0xffffff00);
  for(unsigned i=0;i<64;++i)check(at_end.allocate(4)==i);
  at_end.set(4,63,0xdeadbeef);check(edge.load(0xfffffffc,4)==0xdeadbeef);
  memory::AddressSpace identity;
  kernel::map_thread_identity(identity,0x10000,0x20000,0x12345678);
  check(identity.mapped_bytes()==8);check(identity.load(0x10100,4)==0x20000);check(identity.load(0x2014c,4)==0x12345678);
  fault([&]{identity.load(0x10000,4);});fault([&]{identity.load(0x20000,4);});
  fault([&]{identity.store(0x10100,4,1);});fault([&]{identity.store(0x2014c,4,1);});
  for(auto pcr:{0u,3u,0xfffffeb0u})invalid([&]{kernel::map_thread_identity(identity,pcr,0x30000,1);},"KERNEL_THREAD_IDENTITY_LAYOUT");
  for(auto thread:{0u,3u,0xfffffeb4u})invalid([&]{kernel::map_thread_identity(identity,0x30000,thread,1);},"KERNEL_THREAD_IDENTITY_LAYOUT");
  invalid([&]{kernel::map_thread_identity(identity,0x30000,0x40000,0);},"KERNEL_THREAD_IDENTITY_LAYOUT");
  invalid([&]{kernel::map_thread_identity(identity,0x30000,0x30100,1);},"KERNEL_THREAD_IDENTITY_CONFLICT");
  invalid([&]{kernel::map_thread_identity(identity,0x10000,0x40000,1);},"KERNEL_THREAD_IDENTITY_CONFLICT");
  identity.map(0x40140,1,memory::Access::read);
  invalid([&]{kernel::map_thread_identity(identity,0x30000,0x40000,1);},"KERNEL_THREAD_IDENTITY_CONFLICT");
  check(identity.mapped_bytes()==9);
  fault([&]{identity.load(0x30100,4);});
  std::cout<<"dynamic TLS: "<<checks<<" checks passed; serialized subset only\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
