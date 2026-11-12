#include "kernel/virtual_memory.h"
#include <iostream>
#include <string>
using namespace storm;
int main(){unsigned checks=0;auto check=[&](bool value){++checks;if(!value)throw std::runtime_error("VM check "+std::to_string(checks));};
 auto unavailable=[&](memory::AddressSpace& space,std::uint32_t address){bool caught=false;try{space.load(address,1);}catch(const memory::MemoryFault& e){caught=e.kind()==memory::MemoryFaultKind::unmapped;}check(caught);};
 auto unsupported=[&](auto fn,const char* expected){bool caught=false;try{fn();}catch(const std::runtime_error& e){caught=std::string(e.what())==expected;}check(caught);};
 try{
  memory::AddressSpace space;kernel::VirtualMemory vm(space);std::uint32_t base=0,size=0x100000;
  check(vm.allocate(base,size,0x60002000,4,0)==0);check(base==0x40000000&&size==0x100000&&vm.reservations()==1&&vm.committed_bytes()==0);unavailable(space,base);
  auto original=base;std::uint32_t commit=base+0x10001,amount=1;
  check(vm.allocate(commit,amount,0x1000,4,0)==0);check(commit==base+0x10000&&amount==0x10000&&vm.committed_bytes()==0x10000);check(space.load(commit,8)==0);
  space.store(commit+7,8,UINT64_C(0x0123456789abcdef));amount=0x10000;check(vm.allocate(commit,amount,0x1000,4,0)==0);check(space.load(commit+7,8)==UINT64_C(0x0123456789abcdef));
  amount=0x10000;unsupported([&]{vm.allocate(commit,amount,0x1000,2,0);},"KERNEL_VM_RECOMMIT_PROTECTION_UNIMPLEMENTED");check(space.load(commit+7,8)==UINT64_C(0x0123456789abcdef));
  unavailable(space,base);unavailable(space,base+0x20000);
  std::uint32_t release_size=0;check(vm.free(base,release_size,0x8000)==0);check(base==0&&release_size==0&&vm.committed_bytes()==0&&vm.reservations()==0);unavailable(space,original+0x10000);
  base=0;size=1;check(vm.allocate(base,size,0x3000,2,0)==0);check(base==0x10000&&size==0x1000&&vm.committed_bytes()==0x1000);
  bool caught=false;try{space.store(base,1,1);}catch(const memory::MemoryFault& e){caught=e.kind()==memory::MemoryFaultKind::read_only;}check(caught);
  auto saved=base;std::uint32_t overlap=base,overlap_size=0x1000;check(vm.allocate(overlap,overlap_size,0x2000,4,0)==kernel::VirtualMemory::conflicting_addresses);check(overlap==saved&&overlap_size==0x1000);
  std::uint32_t next=0,next_size=0x1001;check(vm.allocate(next,next_size,0x3000,4,0)==0);check(next==base+0x1000&&next_size==0x2000);
  std::uint32_t top=0,top_size=1;check(vm.allocate(top,top_size,0x103000,4,0)==0);check(top==0x3ffff000&&top_size==0x1000);
  std::uint32_t missing=0x1000000,one=1;check(vm.allocate(missing,one,0x1000,4,0)==kernel::VirtualMemory::conflicting_addresses);check(missing==0x1000000&&one==1);
  std::uint32_t zero=0,zero_size=0;check(vm.allocate(zero,zero_size,0x3000,4,0)==kernel::VirtualMemory::invalid_parameter);
  zero_size=1;check(vm.allocate(zero,zero_size,0,4,0)==kernel::VirtualMemory::invalid_parameter);
  unsupported([&]{vm.allocate(zero,zero_size,0x80003000,4,0);},"KERNEL_VM_ALLOCATION_MODE_UNIMPLEMENTED");
  unsupported([&]{vm.allocate(zero,zero_size,0x3000,4,1);},"KERNEL_VM_ALLOCATION_MODE_UNIMPLEMENTED");
  unsupported([&]{vm.allocate(zero,zero_size,0x3000,0x40,0);},"KERNEL_VM_PROTECTION_UNIMPLEMENTED");
  std::uint32_t negative=0,negative_size=0xfffff001;check(vm.allocate(negative,negative_size,0x3000,4,0)==0);check(negative_size==4096);
  std::uint32_t huge=0,huge_size=0x20100000;auto count=vm.reservations();check(vm.allocate(huge,huge_size,0x20003000,4,0)==kernel::VirtualMemory::no_memory);check(huge==0&&huge_size==0x20100000&&vm.reservations()==count);
  std::uint32_t bad=0x80000000,bad_size=1;check(vm.allocate(bad,bad_size,0x2000,4,0)==kernel::VirtualMemory::conflicting_addresses);
  release_size=1;check(vm.free(saved,release_size,0x8000)==kernel::VirtualMemory::invalid_parameter);
  release_size=0;unsupported([&]{vm.free(saved,release_size,0x4000);},"KERNEL_VM_FREE_MODE_UNIMPLEMENTED");
  std::uint32_t unknown=0x77770000;check(vm.free(unknown,release_size,0x8000)==kernel::VirtualMemory::invalid_parameter);
  memory::AddressSpace partial;kernel::VirtualMemory partial_vm(partial);std::uint32_t reservation=0,reservation_size=8192;
  check(partial_vm.allocate(reservation,reservation_size,0x2000,4,0)==0);partial.map(reservation+4096,16,memory::Access::read);
  std::uint32_t requested=reservation,requested_size=8192;caught=false;try{partial_vm.allocate(requested,requested_size,0x1000,4,0);}catch(const memory::MemoryFault& e){caught=e.kind()==memory::MemoryFaultKind::overlap;}check(caught);
  check(partial.mapped_bytes()==16&&partial_vm.committed_bytes()==0&&partial_vm.reservations()==1&&requested==reservation&&requested_size==8192);unavailable(partial,reservation);
  partial.unmap(reservation+4096);check(partial_vm.allocate(requested,requested_size,0x1000,4,0)==0);check(partial_vm.committed_bytes()==8192);
  memory::AddressSpace crowded;crowded.map(0x10000,0x2000,memory::Access::read);kernel::VirtualMemory crowded_vm(crowded);std::uint32_t first=0,first_size=1;check(crowded_vm.allocate(first,first_size,0x3000,4,0)==0);check(first==0x12000);
  // Repeat allocate/commit/free to prove bytes and address bookkeeping reset.
  memory::AddressSpace repeated;kernel::VirtualMemory repeated_vm(repeated);
  for(unsigned i=0;i<256;i++){std::uint32_t address=0,length=1;check(repeated_vm.allocate(address,length,0x3000,4,0)==0);check(address==0x10000&&repeated.load(address,8)==0);repeated.store(address,8,i+1);length=0;check(repeated_vm.free(address,length,0x8000)==0);check(repeated_vm.committed_bytes()==0&&repeated.mapped_bytes()==0);}
  memory::AddressSpace guest;guest.map(0x80000000,8,memory::Access::read_write);guest.store(0x80000004,4,4096);kernel::VirtualMemory guest_vm(guest);
  check(guest_vm.allocate_guest(0x80000000,0x80000004,0x3000,4,0)==0);check(guest.load(0x80000000,4)==0x10000&&guest.load(0x80000004,4)==4096);
  guest.store(0x80000004,4,0);check(guest_vm.free_guest(0x80000000,0x80000004,0x8000)==0);check(guest.load(0x80000000,4)==0&&guest_vm.reservations()==0);
  check(guest_vm.allocate_guest(0,0x80000004,0x3000,4,0)==kernel::VirtualMemory::invalid_parameter);
  guest.map(0x80000010,4,memory::Access::read);guest.store(0x80000004,4,4096);caught=false;
  try{guest_vm.allocate_guest(0x80000000,0x80000010,0x3000,4,0);}catch(const memory::MemoryFault& e){caught=e.kind()==memory::MemoryFaultKind::read_only;}check(caught);check(guest_vm.reservations()==0&&guest.load(0x80000000,4)==0);
  check(guest_vm.allocate_guest(0x80000000,0x80000004,0,4,0)==kernel::VirtualMemory::invalid_parameter);check(guest.load(0x80000000,4)==0&&guest.load(0x80000004,4)==4096);
  guest.store(0x80000004,4,4096);check(guest_vm.allocate_guest(0x80000000,0x80000004,0x3000,4,0)==0);
  auto self_pointer=std::uint32_t(guest.load(0x80000000,4));guest.store(self_pointer,4,self_pointer);guest.store(0x80000004,4,0);
  unsupported([&]{guest_vm.free_guest(self_pointer,0x80000004,0x8000);},"KERNEL_VM_OUTPUT_IN_RELEASED_REGION_UNIMPLEMENTED");
  check(guest_vm.reservations()==1&&guest.load(self_pointer,4)==self_pointer);
  std::cout<<"virtual memory: "<<checks<<" checks passed; reserve/commit/release only\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
