#include "cpu/context.h"
#include <stdexcept>

namespace storm::cpu {
std::uint32_t Vector128::word(unsigned lane) const {
    if (lane >= 4) throw std::out_of_range("PPC_VECTOR_LANE");
    const unsigned i = lane * 4;
    return (std::uint32_t(bytes[i]) << 24) | (std::uint32_t(bytes[i+1]) << 16) |
           (std::uint32_t(bytes[i+2]) << 8) | bytes[i+3];
}
void Vector128::set_word(unsigned lane, std::uint32_t value) {
    if (lane >= 4) throw std::out_of_range("PPC_VECTOR_LANE");
    const unsigned i = lane * 4;
    for (unsigned j = 0; j < 4; ++j) bytes[i+j] = std::uint8_t(value >> (24 - j*8));
}
Vector128 add_u32(const Vector128& a, const Vector128& b) {
    Vector128 result;
    for (unsigned lane = 0; lane < 4; ++lane) result.set_word(lane, a.word(lane) + b.word(lane));
    return result;
}
Vector128 bit_xor(const Vector128& a, const Vector128& b) {
    Vector128 result;
    for (unsigned i = 0; i < 16; ++i) result.bytes[i] = a.bytes[i] ^ b.bytes[i];
    return result;
}
} // namespace storm::cpu
