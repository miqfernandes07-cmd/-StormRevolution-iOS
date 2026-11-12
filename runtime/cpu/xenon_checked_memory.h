#pragma once
#include "cpu/xenon_bridge.h"
// Scalar accesses only. VMX/atomics that directly index base still require a
// reviewed backend. Do not bind a whole title based on this header alone.
#define PPC_LOAD_U8(address) std::uint8_t(::storm::cpu::load_guest(ctx,base,std::uint32_t(address),1))
#define PPC_LOAD_U16(address) std::uint16_t(::storm::cpu::load_guest(ctx,base,std::uint32_t(address),2))
#define PPC_LOAD_U32(address) std::uint32_t(::storm::cpu::load_guest(ctx,base,std::uint32_t(address),4))
#define PPC_LOAD_U64(address) ::storm::cpu::load_guest(ctx,base,std::uint32_t(address),8)
#define PPC_STORE_U8(address,value) ::storm::cpu::store_guest(ctx,base,std::uint32_t(address),1,std::uint8_t(value))
#define PPC_STORE_U16(address,value) ::storm::cpu::store_guest(ctx,base,std::uint32_t(address),2,std::uint16_t(value))
#define PPC_STORE_U32(address,value) ::storm::cpu::store_guest(ctx,base,std::uint32_t(address),4,std::uint32_t(value))
#define PPC_STORE_U64(address,value) ::storm::cpu::store_guest(ctx,base,std::uint32_t(address),8,std::uint64_t(value))
#define STORM_MMIO_FAULT(address) throw ::storm::cpu::DispatchFault(::storm::cpu::DispatchFaultKind::mmio_unimplemented,std::uint32_t(address))
#define PPC_MM_LOAD_U8(address) (STORM_MMIO_FAULT(address),std::uint8_t(0))
#define PPC_MM_LOAD_U16(address) (STORM_MMIO_FAULT(address),std::uint16_t(0))
#define PPC_MM_LOAD_U32(address) (STORM_MMIO_FAULT(address),std::uint32_t(0))
#define PPC_MM_LOAD_U64(address) (STORM_MMIO_FAULT(address),std::uint64_t(0))
#define PPC_MM_STORE_U8(address,value) STORM_MMIO_FAULT(address)
#define PPC_MM_STORE_U16(address,value) STORM_MMIO_FAULT(address)
#define PPC_MM_STORE_U32(address,value) STORM_MMIO_FAULT(address)
#define PPC_MM_STORE_U64(address,value) STORM_MMIO_FAULT(address)
