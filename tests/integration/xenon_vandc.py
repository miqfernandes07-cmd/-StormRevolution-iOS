#!/usr/bin/env python3
"""Synthetic native vectors for standard VMX VANDC and operand aliasing."""
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
    for name in ('upstream','recompiler','clang','work'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--system-ubsan',action='store_true');args=p.parse_args()
    work,upstream=args.work.resolve(),args.upstream.resolve()
    if not work.is_relative_to(ROOT/'build') or work.exists():p.error('--work must be new and under build/')
    src,dst=work/'input',work/'output';src.mkdir(parents=True);dst.mkdir()
    code=b''.join(struct.pack('>II',4<<26|dest<<21|5<<16|6<<11|1092,0x4e800020) for dest in (4,5,6))
    (src/'vector.o').write_bytes(elf(code));log=run([args.recompiler.resolve(),src,dst]);(work/'generation.log').write_text(log)
    if 'Unrecognized instruction' in log or 'unimplemented' in log:raise RuntimeError('VANDC generation incomplete')
    harness=r'''
#include "output/vector.cpp"
#include <array>
#include <cstdio>
using Fn=void(*)(PPCContext&,uint8_t*);const std::array<Fn,3> funcs{vector_1000,vector_1008,vector_1010};
int main(){unsigned checks=0;uint64_t seed=42;const std::array<uint8_t,8> edge{0,255,170,85,1,128,127,254};
 for(unsigned k=0;k<3;k++)for(unsigned i=0;i<1088;i++){PPCContext c{};alignas(32)uint8_t memory[32]{};std::array<uint8_t,16>a{},b{};
  for(unsigned byte=0;byte<16;byte++){seed=seed*UINT64_C(6364136223846793005)+1;a[byte]=i<64?edge[i/8]:uint8_t(seed>>32);seed=seed*UINT64_C(6364136223846793005)+1;b[byte]=i<64?edge[i%8]:uint8_t(seed>>32);c.v5.u8[byte]=a[byte];c.v6.u8[byte]=b[byte];}
  c.cr0.lt=1;c.cr0.eq=1;c.xer.ca=1;c.xer.so=1;c.r3.u64=123;funcs[k](c,memory);
  PPCVRegister& result=k==0?c.v4:(k==1?c.v5:c.v6);
  for(unsigned byte=0;byte<16;byte++){unsigned want=0;for(unsigned bit=0;bit<8;bit++)if((a[byte]>>bit&1)&&!(b[byte]>>bit&1))want|=1u<<bit;
   if(result.u8[byte]!=want||(k!=1&&c.v5.u8[byte]!=a[byte])||(k!=2&&c.v6.u8[byte]!=b[byte]))return 1;}
  if(c.cr0.lt!=1||c.cr0.eq!=1||c.xer.ca!=1||c.xer.so!=1||c.r3.u64!=123)return 2;++checks;
 }std::printf("VANDC: %u native vectors passed\n",checks);}
'''
    (work/'native.cpp').write_text(harness)
    run([args.clang.absolute(),'-std=c++20','-O2','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(upstream/'XenonUtils'),'-I'+str(upstream/'thirdparty/simde'),work/'native.cpp','-o',work/'native',*(['-fno-sanitize-link-runtime','-lubsan'] if args.system_ubsan else [])]);result=run([work/'native']);assert '3264 native vectors passed' in result
    report={'scope':'synthetic_upstream_generated_host_VMX_bitwise_only','vectors':3264,'host':platform.machine(),'compiler':run([args.clang.absolute(),'--version']).splitlines()[0],'binary_sha256':hashlib.sha256(args.recompiler.read_bytes()).hexdigest(),'patch_sha256':hashlib.sha256((ROOT/'tools/recompilation/patches/0006-vandc.patch').read_bytes()).hexdigest(),'game_executed':False,'result':result.strip()}
    (work/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
