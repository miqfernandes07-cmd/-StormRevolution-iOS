#pragma once
#include "memory/address_space.h"
#include <cstdint>
#include <map>
#include <vector>

namespace storm::kernel {
// Structural view of the original XEX header only. Identity/signature validation
// belongs to the preparation pipeline; this view never authorizes an image.
class XexHeader {
public:
    explicit XexHeader(std::vector<std::uint8_t> bytes);
    std::uint32_t field(std::uint32_t guest_base, std::uint32_t key) const;
    const std::vector<std::uint8_t>& bytes() const noexcept { return bytes_; }
private:
    struct Field { std::uint32_t value, offset; };
    std::vector<std::uint8_t> bytes_;
    std::map<std::uint32_t,Field> fields_;
};
struct ExecutableLayout {
    std::uint32_t variable, descriptor, header;
    std::uint32_t image_base, image_size, entry;
};
// Minimal read-only loader metadata. Only implemented descriptor fields are
// mapped; accesses to other fields fault. No fabricated success for load/unload,
// kernel handles, module enumeration, security or executable privilege checks.
class ExecutableModule {
public:
    ExecutableModule(memory::AddressSpace&, const XexHeader&, ExecutableLayout);
    void bind_handle_slot(std::uint32_t address, std::uint32_t expected_import_word);
    std::uint32_t header_field(std::uint32_t header_pointer,std::uint32_t key) const;
private:
    memory::AddressSpace& memory_;
    XexHeader header_;
    ExecutableLayout layout_;
};
} // namespace storm::kernel
