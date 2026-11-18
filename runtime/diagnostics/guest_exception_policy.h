#pragma once
#include <cstdint>

namespace storm::diagnostics {
// Visual C++ debugger thread-name notification. It carries no game exception
// or return value. All other exception codes, flags and arities are forwarded.
constexpr bool IsOptionalThreadName(std::uint32_t code, std::uint32_t flags,
                                    std::uint32_t parameters) {
  return code == 0x406D1388 && flags == 0 && parameters == 4;
}
}
