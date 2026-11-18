#pragma once
#include "memory/address_space.h"
#include <functional>

namespace storm::kernel {
// Only the observed +16 BE32 uptime field is modeled. The process owner provides
// serialized monotonic uptime in milliseconds; each guest read samples it once.
// This is not a timer thread, scheduler or complete KeTimeStampBundle layout.
class TimestampBundle {
public:
    using UptimeMillis=std::function<std::uint64_t()>;
    TimestampBundle(memory::AddressSpace&,std::uint32_t base,UptimeMillis);
    void bind_import(std::uint32_t slot,std::uint32_t expected);
private:
    memory::AddressSpace& memory_;
    std::uint32_t base_;
};
} // namespace storm::kernel
