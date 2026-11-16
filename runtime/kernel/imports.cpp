#include "kernel/imports.h"
#include <chrono>
#include <stdexcept>

namespace storm::kernel {
void Imports::add(std::string module, std::uint16_t ordinal, Handler handler) {
    if (module.empty() || !handler) throw std::invalid_argument("IMPORT_INVALID_REGISTRATION");
    if (!handlers_.emplace(std::make_pair(std::move(module),ordinal),std::move(handler)).second)
        throw std::invalid_argument("IMPORT_DUPLICATE_REGISTRATION");
}
void Imports::invoke(const std::string& module, std::uint16_t ordinal, cpu::Context& context) const {
    const auto found = handlers_.find({module,ordinal});
    if (found == handlers_.end())
        throw std::runtime_error("IMPORT_UNRESOLVED:"+module+":"+std::to_string(ordinal));
    found->second(context);
}
std::uint64_t filetime_from_unix_nanoseconds(std::int64_t ns) {
    const auto ticks=ns/100-(ns%100<0?1:0);
    return std::uint64_t(INT64_C(116444736000000000)+ticks);
}
std::uint64_t system_time_filetime() {
    return filetime_from_unix_nanoseconds(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count());
}
std::uint64_t monotonic_nanoseconds() {
    return std::uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count());
}
} // namespace storm::kernel
