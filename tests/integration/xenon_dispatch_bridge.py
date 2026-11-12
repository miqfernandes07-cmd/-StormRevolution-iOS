#!/usr/bin/env python3
"""Link actual synthetic Xenon output to the checked native function registry."""
import argparse
import hashlib
import json
import platform
import struct
from pathlib import Path
from xenon_eqv import ROOT,run
from xenon_single_update import elf


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('upstream','recompiler','clang','work'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--system-ubsan',action='store_true');args=p.parse_args();work=args.work.resolve();upstream=args.upstream.resolve()
    if not work.is_relative_to(ROOT/'build') or work.exists():p.error('--work must be new and under build/')
    src,dst=work/'input',work/'output';src.mkdir(parents=True);dst.mkdir()
    # Increment leaf; caller saves LR before BCTRL and restores it before BLR.
    code=struct.pack('>16I',0x38630001,0x4e800020,0x7c0802a6,0x4e800421,0x7c0803a6,0x4e800020,0x7c0802a6,0x7c6803a6,0x4e800021,0x7c0803a6,0x4e800020,0x38840001,0x4e800020,0x80640000,0x90640004,0x4e800020)
    (src/'bridge.o').write_bytes(elf(code));log=run([args.recompiler.resolve(),src,dst]);(work/'generation.log').write_text(log)
    if any(s in log for s in ('Unrecognized instruction','unimplemented','Unable to decode')):raise RuntimeError('Incomplete bridge fixture generation')
    harness=r'''
#include "cpu/xenon_checked_memory.h"
#include "memory/address_space.h"
#include "output/bridge.cpp"
#include <array>
#include <cstdio>
#include <string>
using namespace storm::cpu;
void observe(PPCContext& context,uint8_t*){if(context.lr!=0x1024)throw std::runtime_error("BLRL_LINK_PC");context.r4.u64++;}
int main(){AotFunctionTable table;table.add(0x1000,bridge_1000);table.add(0x1008,bridge_1008);table.add(0x1018,bridge_1018);table.add(0x102c,bridge_102C);table.add(0x3000,observe);table.add(0x1034,bridge_1034);table.seal();unsigned checks=0;
 const std::array<uint64_t,8> inputs{0,1,UINT64_MAX,UINT64_C(0x7fffffffffffffff),UINT64_C(0x8000000000000000),0x7fffffff,0xffffffff,UINT64_C(0x0123456789abcdef)};
 for(auto input:inputs){PPCContext context{};alignas(32)uint8_t memory[32]{};context.r3.u64=input;context.lr=0x12345000;context.ctr.u64=0x1000;
  AotBinding binding(table,context,memory);dispatch(context,memory,0x1008);
  if(context.r3.u64!=input+1||context.lr!=0x12345000||context.ctr.u64!=0x1000)return 1;++checks;
  context.ctr.u64=0x2000;bool missing=false;try{dispatch(context,memory,0x1008);}catch(const DispatchFault& error){missing=error.kind()==DispatchFaultKind::missing_function&&error.address()==0x2000;}
  if(!missing)return 2;++checks;
  context.r3.u64=UINT64_C(0x12340000102f);context.r4.u64=input;context.lr=0x12345000;context.ctr.u64=17;
  dispatch(context,memory,0x1018);
  if(context.r4.u64!=input+1||context.lr!=0x12345000||context.ctr.u64!=17)return 3;++checks;
  context.r3.u64=0x2003;missing=false;try{dispatch(context,memory,0x1018);}catch(const DispatchFault& error){missing=error.kind()==DispatchFaultKind::missing_function&&error.address()==0x2000;}
  if(!missing||context.lr!=0x1024)return 4;++checks;
 }
 {PPCContext context{};uint8_t memory[32]{};context.r3.u64=0x3000;context.lr=0x12345000;AotBinding binding(table,context,memory);dispatch(context,memory,0x1018);if(context.r4.u64!=1||context.lr!=0x12345000)return 5;++checks;}
 for(auto value:inputs){PPCContext context{};alignas(32)uint8_t memory[32]{};storm::memory::AddressSpace space;
  space.map(0x82000000,8,storm::memory::Access::read_write);space.store(0x82000000,4,value);context.r4.u64=0x82000000;
  {AotBinding binding(table,context,memory,&space);dispatch(context,memory,0x1034);if(context.r3.u64!=uint32_t(value)||space.load(0x82000004,4)!=uint32_t(value))return 6;++checks;}
  space.unmap(0x82000000);const uint8_t initial[4]{0x12,0x34,0x56,0x78};space.map(0x82000000,4,storm::memory::Access::read,initial,4);space.map(0x82000004,4,storm::memory::Access::read);
  bool caught=false;{AotBinding binding(table,context,memory,&space);try{dispatch(context,memory,0x1034);}catch(const storm::memory::MemoryFault& error){caught=error.kind()==storm::memory::MemoryFaultKind::read_only&&error.address()==0x82000004;}}
  if(!caught||context.r3.u64!=0x12345678||space.load(0x82000004,4)!=0)return 7;++checks;
 }
 {bool caught=false;try{(void)PPC_MM_LOAD_U32(0xc0000000u);}catch(const DispatchFault& error){caught=error.kind()==DispatchFaultKind::mmio_unimplemented&&error.address()==0xc0000000u;}if(!caught)return 8;++checks;
  caught=false;try{PPC_MM_STORE_U32(0xc0000000u,1);}catch(const DispatchFault& error){caught=error.kind()==DispatchFaultKind::mmio_unimplemented;}if(!caught)return 9;++checks;}
 std::printf("Xenon dispatch bridge: %u native checks passed; no game\n",checks);
}
'''
    (work/'native.cpp').write_text(harness)
    results={}
    for mode,flags in (('elf_alias',[]),('portable_wrapper',['-DPPC_CONFIG_DISABLE_ALIAS'])):
        run([args.clang.absolute(),'-std=c++20','-O2','-fwrapv','-fno-strict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-pthread',*flags,'-I'+str(ROOT/'runtime'),'-I'+str(upstream/'XenonUtils'),'-I'+str(upstream/'thirdparty/simde'),work/'native.cpp',ROOT/'runtime/cpu/aot_dispatch.cpp',ROOT/'runtime/memory/address_space.cpp','-o',work/mode,*(['-fno-sanitize-link-runtime','-lubsan'] if args.system_ubsan else [])])
        result=run([work/mode]);assert '51 native checks passed' in result;results[mode]=result.strip()
    report={'scope':'synthetic_upstream_generated_BCTRL_BLRL_checked_dispatch_and_scalar_memory','checks':102,'host':platform.machine(),'compiler':run([args.clang.absolute(),'--version']).splitlines()[0],'signed_overflow_policy':'fwrapv for PPC modular arithmetic','binary_sha256':hashlib.sha256(args.recompiler.read_bytes()).hexdigest(),'context_sha256':hashlib.sha256((upstream/'XenonUtils/ppc_context.h').read_bytes()).hexdigest(),'game_executed':False,'results':results}
    (work/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
