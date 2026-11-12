#!/usr/bin/env python3
"""Synthetic VX128_5 encodings shadowed by legacy BookE MAC opcode matches."""
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
    p.add_argument('--system-ubsan',action='store_true');args=p.parse_args();work=args.work.resolve();upstream=args.upstream.resolve()
    if not work.is_relative_to(ROOT/'build') or work.exists():p.error('--work must be new and under build/')
    code=b'';rows=[]
    for vd in (64,65,95):
        for va in (3,7):
            for vb in (4,31):
                for shift in (4,12):
                    word=4<<26|(vd&31)<<21|(va&31)<<16|(vb&31)<<11|((va>>6)&1)<<10|shift<<6|((va>>5)&1)<<5|16|((vd>>5)&3)<<2|((vb>>5)&3)
                    code+=struct.pack('>II',word,0x4e800020);rows.append('{%d,%d,%d,%d}'%(vd,va,vb,shift))
    src,dst=work/'input',work/'output';src.mkdir(parents=True);dst.mkdir()
    (src/'shiftvector.o').write_bytes(elf(code));log=run([args.recompiler.resolve(),src,dst]);(work/'generation.log').write_text(log)
    generated=(dst/'shiftvector.cpp').read_text()
    if any(s in log for s in ('Unrecognized instruction','unimplemented','Unable to decode')) or generated.count('// vsldoi128 ')!=len(rows):raise RuntimeError('Xenon VSLDOI128 decoding incomplete')
    harness=r'''
#include "output/shiftvector.cpp"
#include <array>
#include <cstdio>
struct Op{unsigned vd,va,vb,shift;};const std::array<Op,24> ops{{ROWS}};
using Fn=void(*)(PPCContext&,uint8_t*);const std::array<Fn,24> funcs{FUNCTIONS};
PPCVRegister& vr(PPCContext& c,unsigned n){switch(n){case 3:return c.v3;case 7:return c.v7;case 4:return c.v4;case 31:return c.v31;case 64:return c.v64;case 65:return c.v65;default:return c.v95;}}
int main(){uint64_t seed=71;unsigned checks=0;
 for(unsigned k=0;k<24;k++)for(unsigned i=0;i<1088;i++){PPCContext c{};alignas(32)uint8_t memory[32]{};auto op=ops[k];std::array<uint8_t,16>a{},b{};
  for(unsigned byte=0;byte<16;byte++){seed=seed*UINT64_C(6364136223846793005)+1;a[byte]=i<64?uint8_t(byte+i):uint8_t(seed>>32);seed=seed*UINT64_C(6364136223846793005)+1;b[byte]=i<64?uint8_t(255-byte-i):uint8_t(seed>>32);vr(c,op.va).u8[byte]=a[byte];vr(c,op.vb).u8[byte]=b[byte];}
  c.r3.u64=123;c.xer.ca=1;c.xer.so=1;c.cr0.lt=1;funcs[k](c,memory);
  for(unsigned byte=0;byte<16;byte++){unsigned selected=15-byte+op.shift;uint8_t want=selected<16?a[15-selected]:b[31-selected];
    if(vr(c,op.vd).u8[byte]!=want||vr(c,op.va).u8[byte]!=a[byte]||vr(c,op.vb).u8[byte]!=b[byte])return 1;}
  if(c.r3.u64!=123||c.xer.ca!=1||c.xer.so!=1||c.cr0.lt!=1)return 2;++checks;
 }std::printf("Xenon VSLDOI128 decode: %u native vectors passed\n",checks);}
'''.replace('ROWS',','.join(rows)).replace('FUNCTIONS',','.join('shiftvector_%X'%(0x1000+i*8) for i in range(len(rows))))
    (work/'native.cpp').write_text(harness);run([args.clang.absolute(),'-std=c++20','-O2','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(upstream/'XenonUtils'),'-I'+str(upstream/'thirdparty/simde'),work/'native.cpp','-o',work/'native',*(['-fno-sanitize-link-runtime','-lubsan'] if args.system_ubsan else [])]);result=run([work/'native']);assert '26112 native vectors passed' in result
    report={'scope':'synthetic_upstream_generated_host_Xenon_VX128_5_MAC_collision_subset','vectors':26112,'functions':len(rows),'host':platform.machine(),'compiler':run([args.clang.absolute(),'--version']).splitlines()[0],'binary_sha256':hashlib.sha256(args.recompiler.read_bytes()).hexdigest(),'patch_sha256':hashlib.sha256((ROOT/'tools/recompilation/patches/0009-xenon-vsldoi-decode.patch').read_bytes()).hexdigest(),'game_executed':False,'result':result.strip()}
    (work/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
