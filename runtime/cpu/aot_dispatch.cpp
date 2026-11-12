#include "cpu/aot_dispatch.h"
#include <cstdio>
#include <string>

namespace storm::cpu {
namespace {
const char* label(DispatchFaultKind kind) {
    switch(kind) {
    case DispatchFaultKind::invalid_registration:return "AOT_INVALID_REGISTRATION";
    case DispatchFaultKind::duplicate_registration:return "AOT_DUPLICATE_REGISTRATION";
    case DispatchFaultKind::sealed_table:return "AOT_TABLE_SEALED";
    case DispatchFaultKind::unsealed_table:return "AOT_TABLE_NOT_SEALED";
    case DispatchFaultKind::unbound_thread:return "AOT_THREAD_NOT_BOUND";
    case DispatchFaultKind::context_mismatch:return "AOT_CONTEXT_MISMATCH";
    case DispatchFaultKind::memory_mismatch:return "AOT_MEMORY_MISMATCH";
    case DispatchFaultKind::missing_function:return "AOT_FUNCTION_MISSING";
    }
    return "AOT_DISPATCH_FAULT";
}
std::string message(DispatchFaultKind kind,std::uint32_t address) {
    char text[96];std::snprintf(text,sizeof(text),"%s: guest_pc=0x%08X",label(kind),unsigned(address));
    return text;
}
}
thread_local AotBinding::Frame* AotBinding::current_ = nullptr;
DispatchFault::DispatchFault(DispatchFaultKind kind,std::uint32_t address)
    :std::runtime_error(message(kind,address)),kind_(kind),address_(address) {}
void AotFunctionTable::add(std::uint32_t address,AotFunction* function) {
    if(sealed_)throw DispatchFault(DispatchFaultKind::sealed_table,address);
    if(address%4||function==nullptr)throw DispatchFault(DispatchFaultKind::invalid_registration,address);
    if(!functions_.emplace(address,function).second)throw DispatchFault(DispatchFaultKind::duplicate_registration,address);
}
AotFunction* AotFunctionTable::lookup(std::uint32_t address) const {
    if(!sealed_)throw DispatchFault(DispatchFaultKind::unsealed_table,address);
    const auto found=functions_.find(address);
    if(address%4||found==functions_.end())throw DispatchFault(DispatchFaultKind::missing_function,address);
    return found->second;
}
AotBinding::AotBinding(const AotFunctionTable& table,PPCContext& context,std::uint8_t* memory)
    :frame_{&table,&context,memory},previous_(current_) {
    if(!table.sealed())throw DispatchFault(DispatchFaultKind::unsealed_table,0);
    if(memory==nullptr)throw DispatchFault(DispatchFaultKind::memory_mismatch,0);
    current_=&frame_;
}
AotBinding::~AotBinding() noexcept { current_=previous_; }
void dispatch(PPCContext& context,std::uint8_t* memory,std::uint32_t address) {
    const auto* frame=AotBinding::current_;
    if(frame==nullptr)throw DispatchFault(DispatchFaultKind::unbound_thread,address);
    if(frame->context!=&context)throw DispatchFault(DispatchFaultKind::context_mismatch,address);
    if(frame->memory!=memory)throw DispatchFault(DispatchFaultKind::memory_mismatch,address);
    frame->table->lookup(address)(context,memory);
}
} // namespace storm::cpu
