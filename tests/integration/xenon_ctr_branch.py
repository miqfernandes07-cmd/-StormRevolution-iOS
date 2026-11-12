#!/usr/bin/env python3
"""Synthetic native integration for guest32 relative BDZF/BDNZF/BDNZT."""
import argparse
import hashlib
import json
import platform
import struct
from xenon_eqv import ROOT, run
from xenon_single_update import elf
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('upstream','recompiler','clang','work'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--system-ubsan',action='store_true');args=p.parse_args()
    work,upstream=args.work.resolve(),args.upstream.resolve()
    if not work.is_relative_to(ROOT/'build') or work.exists():p.error('--work must be new and under build/')
    src,dst=work/'input',work/'output';src.mkdir(parents=True);dst.mkdir();code=b''
    for bo in (2,0,8):
        for bi in range(32):
            for prediction in (0,1):
                code+=struct.pack('>5I',16<<26|(bo|prediction)<<21|bi<<16|12,
                                  0x38600001,0x48000008,0x38600002,0x4e800020)
    addresses=list(range(0x1000,0x1000+len(code),20))
    for bo in (2,0,8):
        for bi in range(32):
            for prediction in (0,1):
                addresses.append(0x1000+len(code))
                code+=struct.pack('>3I',0x38630001,16<<26|(bo|prediction)<<21|bi<<16|0xfffc,0x4e800020)
    (src/'branches.o').write_bytes(elf(code))
    log=run([args.recompiler.resolve(),src,dst]);(work/'generation.log').write_text(log)
    if 'Unrecognized instruction' in log or 'unimplemented' in log:raise RuntimeError('Incomplete branch generation')
    harness=r'''
#include "output/branches.cpp"
#include <array>
#include <cstdio>
using Fn=void(*)(PPCContext&,uint8_t*);const std::array<Fn,384> functions{FUNCTIONS};
PPCCRRegister& field(PPCContext& c,unsigned n){switch(n){FIELDS}return c.cr0;}
void set(PPCCRRegister& c,unsigned b,unsigned value){switch(b){case 0:c.lt=value;break;case 1:c.gt=value;break;case 2:c.eq=value;break;case 3:c.so=value;}}
unsigned get(PPCCRRegister& c,unsigned b){switch(b){case 0:return c.lt;case 1:return c.gt;case 2:return c.eq;default:return c.so;}}
int main(){unsigned checks=0;
 const std::array<uint64_t,6> counters{0,1,2,UINT64_C(0xffffffff),UINT64_C(0x100000000),UINT64_C(0x100000001)};
 for(unsigned k=0;k<384;k++)for(unsigned bit=0;bit<2;bit++)for(unsigned index=0;index<(k>=192?3:6);index++){
  uint64_t counter=k>=192?index+1:counters[index];
  PPCContext c{};alignas(32)uint8_t mem[32]{};unsigned kind=(k%192)/64,bi=(k%64)/2;
  for(unsigned f=0;f<8;f++)for(unsigned b=0;b<4;b++)set(field(c,f),b,!bit);
  set(field(c,bi/4),bi%4,bit);c.ctr.u64=counter;c.xer.ca=1;c.xer.so=1;c.r4.u64=123;
  functions[k](c,mem);uint64_t after=counter;unsigned iterations=0;bool branch=false;
  do {++iterations;--after;branch=(kind==0?uint32_t(after)==0:uint32_t(after)!=0)&&(kind==2?bit:!bit);}while(k>=192&&branch&&iterations<8);
  if(iterations>=8)return 3;
  uint64_t expected=k>=192?iterations:(branch?2u:1u);
  if(c.r3.u64!=expected||c.ctr.u64!=after||c.r4.u64!=123||c.xer.ca!=1||c.xer.so!=1)return 1;
  for(unsigned f=0;f<8;f++)for(unsigned b=0;b<4;b++)if(get(field(c,f),b)!=((f==bi/4&&b==bi%4)?bit:!bit))return 2;
  ++checks;
 }std::printf("CTR branches: %u native cases passed (guest32 counter test, all CR bits)\n",checks);}
'''.replace('FUNCTIONS',','.join('branches_%X'%address for address in addresses)).replace('FIELDS',''.join('case %d:return c.cr%d;'%(i,i) for i in range(8)))
    (work/'native.cpp').write_text(harness)
    run([args.clang.absolute(),'-std=c++20','-O2','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(upstream/'XenonUtils'),'-I'+str(upstream/'thirdparty/simde'),work/'native.cpp','-o',work/'native',*(['-fno-sanitize-link-runtime','-lubsan'] if args.system_ubsan else [])])
    result=run([work/'native']);assert '3456 native cases passed' in result
    report={'scope':'synthetic_upstream_generated_host_guest32_intra_function_relative_only','cases':3456,'host':platform.machine(),'compiler':run([args.clang.absolute(),'--version']).splitlines()[0],'binary_sha256':hashlib.sha256(args.recompiler.read_bytes()).hexdigest(),'patch_sha256':hashlib.sha256((ROOT/'tools/recompilation/patches/0004-conditional-ctr.patch').read_bytes()).hexdigest(),'game_executed':False,'result':result.strip()}
    (work/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
