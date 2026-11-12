#include "kernel/executable_module.h"
#include <iostream>
#include <string>
#include <vector>
using namespace storm;
namespace {
void put(std::vector<std::uint8_t>& bytes,std::size_t offset,std::uint32_t value){for(unsigned i=0;i<4;i++)bytes.at(offset+i)=std::uint8_t(value>>((3-i)*8));}
std::vector<std::uint8_t> fixture(){std::vector<std::uint8_t> bytes(128);bytes[0]='X';bytes[1]='E';bytes[2]='X';bytes[3]='2';put(bytes,8,128);put(bytes,20,4);
 put(bytes,24,0x100);put(bytes,28,7);put(bytes,32,0x201);put(bytes,36,0x12345678);put(bytes,40,0x302);put(bytes,44,80);put(bytes,48,0x4ff);put(bytes,52,96);put(bytes,96,8);return bytes;}
}
int main(){unsigned checks=0;auto check=[&](bool value){++checks;if(!value)throw std::runtime_error("module check "+std::to_string(checks));};
 auto invalid=[&](auto fn,const char* code){bool caught=false;try{fn();}catch(const std::invalid_argument& e){caught=std::string(e.what())==code;}check(caught);};
 try {
  kernel::XexHeader header(fixture());
  check(header.field(0x80000000,0x100)==7);check(header.field(0x80000000,0x201)==0x80000024);
  check(header.field(0x80000000,0x302)==0x80000050);check(header.field(0x80000000,0x4ff)==0x80000060);check(header.field(0x80000000,0x999)==0);
  invalid([&]{header.field(0xfffffff0,0x100);},"KERNEL_MODULE_ADDRESS_RANGE");
  invalid([&]{header.field(0,0x100);},"KERNEL_MODULE_ADDRESS_RANGE");
  for(unsigned mode=0;mode<10;mode++){
   auto bytes=fixture();const char* code="KERNEL_XEX_HEADER_FORMAT";
   switch(mode){
   case 0:bytes.resize(20);break;
   case 1:bytes[0]=0;break;
   case 2:put(bytes,8,129);code="KERNEL_XEX_HEADER_TABLE";break;
   case 3:put(bytes,20,4097);code="KERNEL_XEX_HEADER_TABLE";break;
   case 4:put(bytes,20,14);code="KERNEL_XEX_HEADER_TABLE";break;
   case 5:put(bytes,32,0x100);code="KERNEL_XEX_HEADER_DUPLICATE";break;
   case 6:put(bytes,44,40);code="KERNEL_XEX_FIELD_OFFSET";break;
   case 7:put(bytes,44,128);code="KERNEL_XEX_FIELD_OFFSET";break;
   case 8:put(bytes,96,0);code="KERNEL_XEX_FIELD_SIZE";break;
   case 9:put(bytes,96,33);code="KERNEL_XEX_FIELD_SIZE";break;
   }
   invalid([&]{kernel::XexHeader bad(bytes);},code);
  }
  const kernel::ExecutableLayout layout{0x80001000,0x80002000,0x80003000,0x82000000,0x1000,0x82000020};
  memory::AddressSpace space;space.map(0x82000000,0x1000,memory::Access::read_write);space.store(0x82000010,4,0x10193);
  kernel::ExecutableModule module(space,header,layout);
  check(space.load(layout.variable,4)==layout.descriptor);
  for(unsigned offset=0;offset<24;offset+=8){check(space.load(layout.descriptor+offset,4)==layout.descriptor+offset);check(space.load(layout.descriptor+offset+4,4)==layout.descriptor+offset);}
  check(space.load(layout.descriptor+0x18,4)==layout.image_base);check(space.load(layout.descriptor+0x1c,4)==layout.image_base);
  check(space.load(layout.descriptor+0x20,4)==layout.image_size);check(space.load(layout.descriptor+0x3c,4)==layout.entry);
  check(space.load(layout.descriptor+0x40,2)==1);check(space.load(layout.descriptor+0x58,4)==layout.header);
  module.bind_handle_slot(0x82000010,0x10193);check(space.load(0x82000010,4)==layout.variable);
  invalid([&]{module.bind_handle_slot(0x82000010,0x10193);},"KERNEL_EXECUTABLE_HANDLE_IMPORT_MISMATCH");
  space.store(0x82000010,4,0x10194);invalid([&]{module.bind_handle_slot(0x82000010,0x10194);},"KERNEL_EXECUTABLE_HANDLE_IMPORT_MISMATCH");
  space.store(0x82000010,4,0x10193);invalid([&]{module.bind_handle_slot(0x82000010,0x10010193);},"KERNEL_EXECUTABLE_HANDLE_IMPORT_MISMATCH");
  check(module.header_field(layout.header,0x201)==layout.header+36);check(space.load(layout.header+36,4)==0x12345678);
  check(module.header_field(layout.header,0x999)==0);
  invalid([&]{module.header_field(layout.header+4,0x201);},"KERNEL_XEX_HEADER_UNKNOWN_MODULE");
  bool caught=false;try{space.load(layout.descriptor+0x24,4);}catch(const memory::MemoryFault& e){caught=e.kind()==memory::MemoryFaultKind::unmapped;}check(caught);
  caught=false;try{space.store(layout.header+36,4,0);}catch(const memory::MemoryFault& e){caught=e.kind()==memory::MemoryFaultKind::read_only;}check(caught);
  memory::AddressSpace conflict;conflict.map(layout.descriptor+0x40,2,memory::Access::read);
  caught=false;try{kernel::ExecutableModule duplicate(conflict,header,layout);}catch(const memory::MemoryFault& e){caught=e.kind()==memory::MemoryFaultKind::overlap;}check(caught);check(conflict.mapped_bytes()==2);
  auto broken=layout;broken.entry=layout.image_base+layout.image_size;invalid([&]{kernel::ExecutableModule bad(conflict,header,broken);},"KERNEL_MODULE_LAYOUT");
  check(conflict.mapped_bytes()==2);
  std::cout<<"executable module: "<<checks<<" checks passed; loader metadata only\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
