#include "kernel/executable_module.h"
#include <cstring>
#include <stdexcept>
#include <utility>

namespace storm::kernel {
namespace {
std::uint32_t word(const std::vector<std::uint8_t>& data,std::size_t offset) {
    if(offset>data.size()||data.size()-offset<4)throw std::invalid_argument("KERNEL_XEX_HEADER_BOUNDS");
    return std::uint32_t(data[offset])<<24|std::uint32_t(data[offset+1])<<16|std::uint32_t(data[offset+2])<<8|data[offset+3];
}
void store(std::vector<std::uint8_t>& data,std::size_t offset,std::uint32_t value) {
    for(unsigned i=0;i<4;i++)data.at(offset+i)=std::uint8_t(value>>((3-i)*8));
}
void region(std::uint32_t base,std::size_t size) {
    if(!base||!size||size>(UINT64_C(1)<<32)-base)throw std::invalid_argument("KERNEL_MODULE_ADDRESS_RANGE");
}
}
XexHeader::XexHeader(std::vector<std::uint8_t> bytes):bytes_(std::move(bytes)) {
    if(bytes_.size()<24||bytes_.size()>16*1024*1024||std::memcmp(bytes_.data(),"XEX2",4)!=0)
        throw std::invalid_argument("KERNEL_XEX_HEADER_FORMAT");
    const auto size=word(bytes_,8),count=word(bytes_,20);
    if(size!=bytes_.size()||count>4096||24ULL+std::uint64_t(count)*8>size)
        throw std::invalid_argument("KERNEL_XEX_HEADER_TABLE");
    const auto table_end=24+count*8;
    for(std::uint32_t i=0;i<count;i++) {
        const auto key=word(bytes_,24+i*8),value=word(bytes_,28+i*8),kind=key&255;
        if(fields_.find(key)!=fields_.end())throw std::invalid_argument("KERNEL_XEX_HEADER_DUPLICATE");
        if(kind>1) {
            if(value<table_end||value>=size)throw std::invalid_argument("KERNEL_XEX_FIELD_OFFSET");
            const auto length=kind==255?word(bytes_,value):kind*4;
            if(length<4||length>size-value)throw std::invalid_argument("KERNEL_XEX_FIELD_SIZE");
        }
        fields_.emplace(key,Field{value,28+i*8});
    }
}
std::uint32_t XexHeader::field(std::uint32_t base,std::uint32_t key) const {
    region(base,bytes_.size());const auto found=fields_.find(key);
    if(found==fields_.end())return 0;
    if((key&255)==0)return found->second.value;
    return base+((key&255)==1?found->second.offset:found->second.value);
}
ExecutableModule::ExecutableModule(memory::AddressSpace& memory,const XexHeader& header,ExecutableLayout layout)
    :memory_(memory),header_(header),layout_(layout) {
    region(layout.variable,4);region(layout.descriptor,0x64);region(layout.header,header.bytes().size());
    region(layout.image_base,layout.image_size);
    if(layout.variable%4||layout.descriptor%4||layout.header%4||layout.entry<layout.image_base||std::uint64_t(layout.entry)>=std::uint64_t(layout.image_base)+layout.image_size)
        throw std::invalid_argument("KERNEL_MODULE_LAYOUT");
    std::vector<std::uint32_t> mapped;mapped.reserve(6);
    auto add=[&](std::uint32_t address,const std::vector<std::uint8_t>& bytes){memory_.map(address,bytes.size(),memory::Access::read,bytes.data(),bytes.size());mapped.push_back(address);};
    try {
        add(layout.header,header.bytes());
        std::vector<std::uint8_t> cell(4);store(cell,0,layout.descriptor);add(layout.variable,cell);
        std::vector<std::uint8_t> lists_and_image(0x24);
        for(unsigned offset=0;offset<0x18;offset+=8){store(lists_and_image,offset,layout.descriptor+offset);store(lists_and_image,offset+4,layout.descriptor+offset);}
        store(lists_and_image,0x18,layout.image_base);store(lists_and_image,0x1c,layout.image_base);store(lists_and_image,0x20,layout.image_size);add(layout.descriptor,lists_and_image);
        std::vector<std::uint8_t> entry(4);store(entry,0,layout.entry);add(layout.descriptor+0x3c,entry);
        std::vector<std::uint8_t> load_count{0,1};add(layout.descriptor+0x40,load_count);
        std::vector<std::uint8_t> header_pointer(4);store(header_pointer,0,layout.header);add(layout.descriptor+0x58,header_pointer);
    }catch(...) {
        for(auto it=mapped.rbegin();it!=mapped.rend();++it)memory_.unmap(*it);
        throw;
    }
}
void ExecutableModule::bind_handle_slot(std::uint32_t address,std::uint32_t expected) {
    if((expected>>24)!=0||(expected&65535)!=0x193||memory_.load(address,4)!=expected)
        throw std::invalid_argument("KERNEL_EXECUTABLE_HANDLE_IMPORT_MISMATCH");
    memory_.store(address,4,layout_.variable);
}
std::uint32_t ExecutableModule::header_field(std::uint32_t pointer,std::uint32_t key) const {
    if(pointer!=layout_.header)throw std::invalid_argument("KERNEL_XEX_HEADER_UNKNOWN_MODULE");
    return header_.field(layout_.header,key);
}
} // namespace storm::kernel
