#!/usr/bin/env python3
"""Synthetic integration for RLDICL/CLRLDI/ROTLDI and guest32 CR0 record policy."""
import argparse
import hashlib
import json
import platform
import struct
from pathlib import Path
from xenon_eqv import ROOT, run
from xenon_single_update import elf


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('upstream','recompiler','clang','work'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--system-ubsan',action='store_true');args=p.parse_args()
    work,upstream=args.work.resolve(),args.upstream.resolve()
    if not work.is_relative_to(ROOT/'build') or work.exists():p.error('--work must be new and under build/')
    boundaries=(0,1,31,32,63)
    pairs=sorted({(shift,1) for shift in range(64)}|{(1,mask) for mask in range(64)}|{(shift,mask) for shift in boundaries for mask in boundaries})
    code=b'';rows=[]
    for shift,mask in pairs:
        for record in (0,1):
            for alias in (0,1):
                dest=4 if alias else 3
                # MD form: split SH high bit in bit 1; MB high bit in bit 5.
                word=30<<26|4<<21|dest<<16|(shift&31)<<11|(mask&31)<<6|(mask&32)|(shift>>5)<<1|record
                code+=struct.pack('>II',word,0x4e800020);rows.append('{%d,%d,%d,%d}'%(shift,mask,record,dest))
    src,dst=work/'input',work/'output';src.mkdir(parents=True);dst.mkdir()
    (src/'rotate.o').write_bytes(elf(code));log=run([args.recompiler.resolve(),src,dst]);(work/'generation.log').write_text(log)
    if any(message in log for message in ('Unrecognized instruction','unimplemented','no comparison','Unable to decode')):
        raise RuntimeError('Incomplete rotate/record generation; inspect synthetic log')
    count=len(rows);expected=count*72*2
    harness=r'''
#include "output/rotate.cpp"
#include <array>
#include <cstdio>
struct Op{unsigned shift,mask,record,dest;};const std::array<Op,COUNT> ops{{ROWS}};
using Fn=void(*)(PPCContext&,uint8_t*);const std::array<Fn,COUNT> funcs{FUNCTIONS};
uint64_t reference(uint64_t source,unsigned shift,unsigned mask){uint64_t value=0;
 for(unsigned bit=0;bit<64-mask;bit++)if(source>>((bit+64-shift)%64)&1)value|=UINT64_C(1)<<bit;return value;}
int main(){uint64_t seed=19;unsigned checks=0;const std::array<uint64_t,8> edges{0,UINT64_MAX,1,0x7fffffff,0x80000000,UINT64_C(0x100000000),UINT64_C(0x8000000000000000),UINT64_C(0x0123456789abcdef)};
 for(unsigned k=0;k<ops.size();k++)for(unsigned i=0;i<72;i++)for(unsigned so=0;so<2;so++){
  seed=seed*UINT64_C(6364136223846793005)+1;uint64_t source=i<8?edges[i]:seed;PPCContext c{};alignas(32)uint8_t memory[32]{};auto op=ops[k];
  c.r3.u64=123;c.r4.u64=source;c.r5.u64=456;c.xer.ca=1;c.xer.ov=1;c.xer.so=so;c.cr0.lt=1;c.cr0.gt=0;c.cr0.eq=1;c.cr0.so=!so;c.cr1.lt=1;
  uint64_t want=reference(source,op.shift,op.mask);funcs[k](c,memory);uint64_t actual=op.dest==3?c.r3.u64:c.r4.u64;
  if(actual!=want||c.r5.u64!=456||c.xer.ca!=1||c.xer.ov!=1||c.xer.so!=so||c.cr1.lt!=1)return 1;
  if((op.dest!=4&&c.r4.u64!=source)||(op.dest!=3&&c.r3.u64!=123))return 2;
  if(op.record){uint32_t low=uint32_t(want);if(c.cr0.lt!=(low>>31)||c.cr0.gt!=(!(low>>31)&&low!=0)||c.cr0.eq!=(low==0)||c.cr0.so!=so)return 3;}
  else if(c.cr0.lt!=1||c.cr0.gt!=0||c.cr0.eq!=1||c.cr0.so!=!so)return 4;
  ++checks;
 }std::printf("rotate/record: %u native cases passed; guest32 CR0 policy\n",checks);}
'''.replace('COUNT',str(count)).replace('ROWS',','.join(rows)).replace('FUNCTIONS',','.join('rotate_%X'%(0x1000+i*8) for i in range(count)))
    (work/'native.cpp').write_text(harness)
    run([args.clang.absolute(),'-std=c++20','-O2','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(upstream/'XenonUtils'),'-I'+str(upstream/'thirdparty/simde'),work/'native.cpp','-o',work/'native',*(['-fno-sanitize-link-runtime','-lubsan'] if args.system_ubsan else [])])
    result=run([work/'native']);assert f'{expected} native cases passed' in result
    report={'scope':'synthetic_upstream_generated_host_rotate64_guest32_CR0_policy','cases':expected,'functions':count,'shift_mask_pairs':len(pairs),'host':platform.machine(),'compiler':run([args.clang.absolute(),'--version']).splitlines()[0],'binary_sha256':hashlib.sha256(args.recompiler.read_bytes()).hexdigest(),'patch_sha256':hashlib.sha256((ROOT/'tools/recompilation/patches/0008-rldicl-record.patch').read_bytes()).hexdigest(),'game_executed':False,'result':result.strip()}
    (work/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
