#pragma once
#include <cstdint>
#include <stdexcept>
#include <unordered_map>

// Opaque here; the linked AOT image supplies the reviewed Xenon context layout.
struct PPCContext;
namespace storm::cpu {
using AotFunction = void(PPCContext&, std::uint8_t*);
enum class DispatchFaultKind { invalid_registration, duplicate_registration, sealed_table,
    unsealed_table, unbound_thread, context_mismatch, memory_mismatch, missing_function };
class DispatchFault : public std::runtime_error {
public:
    DispatchFault(DispatchFaultKind kind, std::uint32_t address);
    DispatchFaultKind kind() const noexcept { return kind_; }
    std::uint32_t address() const noexcept { return address_; }
private:
    DispatchFaultKind kind_;
    std::uint32_t address_;
};
class AotFunctionTable {
public:
    AotFunctionTable() = default;
    AotFunctionTable(const AotFunctionTable&) = delete;
    AotFunctionTable& operator=(const AotFunctionTable&) = delete;
    AotFunctionTable(AotFunctionTable&&) = delete;
    AotFunctionTable& operator=(AotFunctionTable&&) = delete;
    void add(std::uint32_t address, AotFunction* function);
    void seal() noexcept { sealed_ = true; }
    bool sealed() const noexcept { return sealed_; }
    AotFunction* lookup(std::uint32_t address) const;
private:
    std::unordered_map<std::uint32_t,AotFunction*> functions_;
    bool sealed_ = false;
};
// Bind on every guest thread, after registration is sealed. The owner must keep
// the table, context and memory alive until all bindings/guest calls have ended.
class AotBinding {
public:
    AotBinding(const AotFunctionTable&, PPCContext&, std::uint8_t* memory);
    ~AotBinding() noexcept;
    AotBinding(const AotBinding&) = delete;
    AotBinding& operator=(const AotBinding&) = delete;
    AotBinding(AotBinding&&) = delete;
    AotBinding& operator=(AotBinding&&) = delete;
private:
    struct Frame { const AotFunctionTable* table; PPCContext* context; std::uint8_t* memory; };
    Frame frame_;
    Frame* previous_;
    static thread_local Frame* current_;
    friend void dispatch(PPCContext&,std::uint8_t*,std::uint32_t);
};
void dispatch(PPCContext&,std::uint8_t* memory,std::uint32_t address);
} // namespace storm::cpu
