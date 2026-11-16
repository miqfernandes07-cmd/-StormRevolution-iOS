#pragma once

#include "cpu/context.h"
#include <cstdint>
#include <functional>
#include <map>
#include <string>
#include <utility>

namespace storm::kernel {
// Register only verified implementations; unknown imports must never return fake success.
class Imports {
public:
    using Handler = std::function<void(cpu::Context&)>;
    void add(std::string module, std::uint16_t ordinal, Handler handler);
    void invoke(const std::string& module, std::uint16_t ordinal, cpu::Context& context) const;
private:
    std::map<std::pair<std::string,std::uint16_t>, Handler> handlers_;
};
std::uint64_t monotonic_nanoseconds();
// Windows FILETIME: 100 ns ticks since 1601-01-01 UTC. Negative sub-tick Unix
// timestamps round down, rather than towards zero, across the epoch boundary.
std::uint64_t filetime_from_unix_nanoseconds(std::int64_t nanoseconds);
std::uint64_t system_time_filetime();
} // namespace storm::kernel
