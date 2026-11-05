#pragma once

#include <array>
#include <cstdint>

namespace storm::cpu {
// Guest representation, independent of host ABI and endianness. Full PPC/FPSCR,
// VMX128 and reservation semantics are not implemented by the synthetic backend.
struct Context {
    std::array<std::uint64_t, 32> gpr{};
    std::uint64_t lr{};
    std::uint64_t ctr{};
    std::uint32_t cr{};
};

struct Vector128 {
    std::array<std::uint8_t, 16> bytes{};
    std::uint32_t word(unsigned lane) const;
    void set_word(unsigned lane, std::uint32_t value);
};
Vector128 add_u32(const Vector128& a, const Vector128& b);
Vector128 bit_xor(const Vector128& a, const Vector128& b);
} // namespace storm::cpu
