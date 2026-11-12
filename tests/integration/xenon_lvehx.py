#!/usr/bin/env python3
"""Synthetic test of Xenon LVEHX full-vector behavior referenced by pinned Xenia."""
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
    code=b''.join(struct.pack('>II',31<<26|4<<21|ra<<16|rb<<11|39<<1,0x4e800020) for ra,rb in ((3,5),(0,5),(3,3)))
    (src/'loadvector.o').write_bytes(elf(code));log=run([args.recompiler.resolve(),src,dst]);(work/'generation.log').write_text(log)
    if 'Unrecognized instruction' in log or 'unimplemented' in log:raise RuntimeError('LVEHX generation incomplete')
    harness=r'''
#include "output/loadvector.cpp"
#include <array>
#include <cstdio>
using Fn=void(*)(PPCContext&,uint8_t*);const std::array<Fn,3> funcs{loadvector_1000,loadvector_1008,loadvector_1010};
int main(){unsigned checks=0;uint64_t seed=11;
 for(unsigned k=0;k<3;k++)for(unsigned pattern=0;pattern<128;pattern++)for(unsigned offset=0;offset<64;offset++){
  PPCContext c{};alignas(32)std::array<uint8_t,128> memory{};
  for(unsigned b=0;b<128;b++){seed=seed*UINT64_C(6364136223846793005)+1;memory[b]=pattern<64?uint8_t(b*(pattern+1)):uint8_t(seed>>32);}
  uint32_t ea=k==2?offset*2:offset;c.r0.u64=999;c.r3.u64=k==2?offset:UINT64_C(0x12340000fffffff0);c.r5.u64=k==1?ea:ea+16;
  uint64_t old3=c.r3.u64,old5=c.r5.u64;c.xer.ca=1;c.xer.so=1;c.cr0.lt=1;auto before=memory;
  funcs[k](c,memory.data());for(unsigned b=0;b<16;b++)if(c.v4.u8[b]!=memory[(ea&~15u)+15-b])return 1;
  if(c.r0.u64!=999||c.r3.u64!=old3||c.r5.u64!=old5||c.xer.ca!=1||c.xer.so!=1||c.cr0.lt!=1||memory!=before)return 2;++checks;
 }std::printf("Xenon LVEHX: %u native vectors passed\n",checks);}
'''
    (work/'native.cpp').write_text(harness);run([args.clang.absolute(),'-std=c++20','-O2','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(upstream/'XenonUtils'),'-I'+str(upstream/'thirdparty/simde'),work/'native.cpp','-o',work/'native',*(['-fno-sanitize-link-runtime','-lubsan'] if args.system_ubsan else [])]);result=run([work/'native']);assert '24576 native vectors passed' in result
    report={'scope':'synthetic_upstream_generated_host_Xenon_LVEHX_full_vector_policy','vectors':24576,'host':platform.machine(),'compiler':run([args.clang.absolute(),'--version']).splitlines()[0],'binary_sha256':hashlib.sha256(args.recompiler.read_bytes()).hexdigest(),'patch_sha256':hashlib.sha256((ROOT/'tools/recompilation/patches/0007-lvehx-xenon.patch').read_bytes()).hexdigest(),'game_executed':False,'result':result.strip()}
    (work/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
