#pragma once
#include "cpu/aot_dispatch.h"
// Force-include before the reviewed ppc_context.h in a private AOT target.
// Every target must compile against the same context layout and register its
// actual compiled functions. No decoder, JIT or fabricated fallback is used.
#ifndef PPC_CALL_INDIRECT_FUNC
#define PPC_CALL_INDIRECT_FUNC(address) ::storm::cpu::dispatch(ctx, base, std::uint32_t(address))
#endif
