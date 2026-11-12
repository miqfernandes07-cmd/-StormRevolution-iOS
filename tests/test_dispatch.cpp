#include "cpu/aot_dispatch.h"
#include "memory/address_space.h"
#include <array>
#include <atomic>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
// Test-owned opaque layout; the dispatch implementation never inspects it.
struct PPCContext { std::uint64_t result=0; };
using namespace storm::cpu;
namespace {
unsigned checks=0;
void check(bool value){++checks;if(!value)throw std::runtime_error("dispatch test failed");}
template<class F>void fault(F callback,DispatchFaultKind kind,std::uint32_t pc){
    bool caught=false;try{callback();}catch(const DispatchFault& error){caught=error.kind()==kind&&error.address()==pc&&std::string(error.what()).find("guest_pc=0x")!=std::string::npos;}check(caught);
}
void increment(PPCContext& c,std::uint8_t* memory){++c.result;++memory[0];}
void nested(PPCContext& c,std::uint8_t* memory){dispatch(c,memory,0x1000);dispatch(c,memory,0x1000);}
void failure(PPCContext&,std::uint8_t*){throw std::runtime_error("synthetic native handler failure");}
}
int main(){try{
 AotFunctionTable functions;PPCContext context{},other{};std::array<std::uint8_t,16> memory{},alternate{};
 fault([&]{AotBinding binding(functions,context,memory.data());},DispatchFaultKind::unsealed_table,0);
 fault([&]{functions.add(0x1001,increment);},DispatchFaultKind::invalid_registration,0x1001);
 fault([&]{functions.add(0x1000,nullptr);},DispatchFaultKind::invalid_registration,0x1000);
 functions.add(0x1000,increment);functions.add(0x1004,nested);functions.add(0x1008,failure);
 fault([&]{functions.add(0x1000,increment);},DispatchFaultKind::duplicate_registration,0x1000);
 functions.seal();fault([&]{functions.add(0x1010,increment);},DispatchFaultKind::sealed_table,0x1010);
 fault([&]{dispatch(context,memory.data(),0x1000);},DispatchFaultKind::unbound_thread,0x1000);
 fault([&]{AotBinding binding(functions,context,nullptr);},DispatchFaultKind::memory_mismatch,0);
 {
  AotBinding binding(functions,context,memory.data());dispatch(context,memory.data(),0x1004);check(context.result==2&&memory[0]==2);
  fault([&]{dispatch(other,memory.data(),0x1000);},DispatchFaultKind::context_mismatch,0x1000);
  fault([&]{dispatch(context,alternate.data(),0x1000);},DispatchFaultKind::memory_mismatch,0x1000);
  fault([&]{dispatch(context,memory.data(),0x2000);},DispatchFaultKind::missing_function,0x2000);
  fault([&]{dispatch(context,memory.data(),0x1001);},DispatchFaultKind::missing_function,0x1001);
  fault([&]{load_guest(context,memory.data(),0x80000000,4);},DispatchFaultKind::memory_not_bound,0x80000000);
  fault([&]{store_guest(context,memory.data(),0x80000000,4,1);},DispatchFaultKind::memory_not_bound,0x80000000);
  storm::memory::AddressSpace space;space.map(0x80000000,8,storm::memory::Access::read_write);
  {AotBinding checked(functions,context,memory.data(),&space);store_guest(context,memory.data(),0x80000000,8,UINT64_C(0x0123456789abcdef));check(load_guest(context,memory.data(),0x80000000,8)==UINT64_C(0x0123456789abcdef));
   fault([&]{load_guest(other,memory.data(),0x80000000,4);},DispatchFaultKind::context_mismatch,0x80000000);}
  fault([&]{load_guest(context,memory.data(),0x80000000,4);},DispatchFaultKind::memory_not_bound,0x80000000);
  bool propagated=false;try{dispatch(context,memory.data(),0x1008);}catch(const std::runtime_error& error){propagated=std::string(error.what())=="synthetic native handler failure";}check(propagated);
  try{AotBinding inner(functions,other,alternate.data());dispatch(other,alternate.data(),0x1000);throw std::runtime_error("scope exit");}catch(const std::runtime_error&){}
  dispatch(context,memory.data(),0x1000);check(context.result==3&&other.result==1);
 }
 fault([&]{dispatch(context,memory.data(),0x1000);},DispatchFaultKind::unbound_thread,0x1000);
 std::atomic<bool> correct{true};std::array<std::thread,4> threads;
 for(auto& thread:threads)thread=std::thread([&]{PPCContext c{};std::array<std::uint8_t,16> bytes{};try{AotBinding binding(functions,c,bytes.data());for(unsigned i=0;i<100;i++)dispatch(c,bytes.data(),0x1000);if(c.result!=100||bytes[0]!=100)correct=false;}catch(...){correct=false;}});
 for(auto& thread:threads)thread.join();check(correct);
 std::cout<<"dispatch: "<<checks<<" checks passed; compiled handlers only, no game\n";
 return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
