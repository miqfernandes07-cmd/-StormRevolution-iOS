#!/usr/bin/env python3
"""Own PPC fixtures for checked lwarx/stwcx; no commercial code or inputs."""
import argparse
import importlib.util
import json
import platform
import struct
from pathlib import Path
from xenon_eqv import ROOT,run
from xenon_single_update import elf


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('upstream','recompiler','clang','work'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--system-ubsan',action='store_true');a=p.parse_args()
    work=a.work.resolve();up=a.upstream.resolve()
    if not work.is_relative_to(ROOT/'build') or work.exists():p.error('new --work under build/ required')
    src=work/'input';out=work/'output';src.mkdir(parents=True);out.mkdir()
    # lwarx r3,0,r4; blr; stwcx. r5,0,r4; blr.
    words=[(31<<26)|(3<<21)|(4<<11)|(20<<1),0x4e800020,
           (31<<26)|(5<<21)|(4<<11)|(150<<1)|1,0x4e800020]
    (src/'reserve.o').write_bytes(elf(struct.pack('>4I',*words)))
    log=run([a.recompiler.resolve(),src,out]);(work/'generation.log').write_text(log)
    spec=importlib.util.spec_from_file_location('prefix',ROOT/'tools/recompilation/prefix_probe.py');probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
    original=(out/'reserve.cpp').read_text();adapted=probe.checked_reservations(original)
    if 'PPC_LOAD_RESERVE_U32' not in adapted or 'PPC_STORE_CONDITIONAL_U32' not in adapted or '__sync_' in adapted or 'base +' in adapted:
        raise RuntimeError('unsupported pinned emitter reservation form')
    (out/'reserve.cpp').write_text(adapted)
    harness=r'''
#include "cpu/xenon_checked_memory.h"
#include "output/reserve.cpp"
#include <cstdio>
using namespace storm;
int main(){unsigned checks=0;cpu::AotFunctionTable table;table.add(0x1000,reserve_1000);table.add(0x1008,reserve_1008);table.seal();
 for(uint32_t value:{0u,1u,0x7fffffffu,0x80000000u,0xffffffffu})for(unsigned so:{0u,1u}){
  PPCContext ctx{};uint8_t base[1]{};memory::AddressSpace memory;memory.map(0x80000000,256,memory::Access::read_write);memory.store(0x80000000,4,value);
  cpu::AotBinding binding(table,ctx,base,&memory);ctx.r4.u64=UINT64_C(0x1234000080000000);ctx.xer.so=so;
  cpu::dispatch(ctx,base,0x1000);if(ctx.r3.u64!=value)return 1;++checks;
  ctx.r5.u64=uint32_t(value+1);ctx.cr0.lt=1;ctx.cr0.gt=1;cpu::dispatch(ctx,base,0x1008);
  if(!ctx.cr0.eq||ctx.cr0.lt||ctx.cr0.gt||ctx.cr0.so!=so||memory.load(0x80000000,4)!=uint32_t(value+1))return 2;++checks;
  cpu::dispatch(ctx,base,0x1008);if(ctx.cr0.eq)return 3;++checks;
  cpu::dispatch(ctx,base,0x1000);memory.store(0x80000000,4,value+2);memory.store(0x80000000,4,uint32_t(value+1));
  cpu::dispatch(ctx,base,0x1008);if(ctx.cr0.eq||memory.load(0x80000000,4)!=uint32_t(value+1))return 4;++checks;
  cpu::dispatch(ctx,base,0x1000);memory.store(0x80000080,4,0);cpu::dispatch(ctx,base,0x1008);if(!ctx.cr0.eq)return 5;++checks;
 }
 std::printf("Checked reservation fixture: %u checks; no title\n",checks);
}
'''
    (work/'native.cpp').write_text(harness)
    cmd=[a.clang.absolute(),'-std=c++20','-O2','-fwrapv','-fno-strict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(ROOT/'runtime'),'-I'+str(up/'XenonUtils'),'-I'+str(up/'thirdparty/simde'),work/'native.cpp',ROOT/'runtime/cpu/aot_dispatch.cpp',ROOT/'runtime/memory/address_space.cpp','-o',work/'native']
    if a.system_ubsan:cmd+=['-fno-sanitize-link-runtime','-lubsan']
    run(cmd);result=run([work/'native'])
    if '50 checks' not in result:raise RuntimeError('fixture count mismatch')
    report={'checks':50,'host':platform.machine(),'scope':'own_emitted_guest32_reservations_CR0_and_ABA','game_executed':False,'result':result.strip()}
    (work/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
