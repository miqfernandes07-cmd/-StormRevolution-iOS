#!/usr/bin/env python3
"""Guest32 CA/CR0 policy tests for experimental ADDC/SUBFZE/ADDME native emission."""
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
    for key in ('upstream','recompiler','clang','work'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--system-ubsan',action='store_true');args=p.parse_args()
    work,upstream=args.work.resolve(),args.upstream.resolve()
    if not work.is_relative_to(ROOT/'build') or work.exists():p.error('--work must be new and under build/')
    code=b'';invalid=b''
    for xo in (10,200,234):
        for record in (0,1):
            for dest in (3,4,5):
                code+=struct.pack('>II',31<<26|dest<<21|4<<16|(5<<11 if xo==10 else 0)|xo<<1|record,0x4e800020)
            invalid+=struct.pack('>II',31<<26|3<<21|4<<16|(5<<11 if xo==10 else 0)|(xo|512)<<1|record,0x4e800020)
    for name,body in (('valid',code),('invalid',invalid)):
        src,dst=work/name/'input',work/name/'output';src.mkdir(parents=True);dst.mkdir()
        (src/'carry.o').write_bytes(elf(body));log=run([args.recompiler.resolve(),src,dst]);(work/name/'generation.log').write_text(log)
        if name=='valid' and ('Unrecognized instruction' in log or 'unimplemented' in log or 'no comparison' in log):raise RuntimeError('Carry generation incomplete')
        if name=='invalid' and log.count('Unrecognized instruction')!=6:raise RuntimeError('OE variants must remain rejected')
    harness=r'''
#include "valid/output/carry.cpp"
#include <array>
#include <cstdio>
using Fn=void(*)(PPCContext&,uint8_t*);const std::array<Fn,18> funcs{FUNCTIONS};
uint64_t serial(uint64_t a,uint64_t b,unsigned input,unsigned width,unsigned& output){uint64_t result=0;unsigned carry=input;
 for(unsigned bit=0;bit<width;bit++){unsigned sum=unsigned(a>>bit&1)+unsigned(b>>bit&1)+carry;result|=uint64_t(sum&1)<<bit;carry=sum>>1;}output=carry;return result;}
int main(){const std::array<uint64_t,8> edges{0,1,0x7fffffff,0x80000000,0xffffffff,UINT64_C(0x100000000),UINT64_C(0x8000000000000000),UINT64_MAX};unsigned checks=0;uint64_t seed=17;
 for(unsigned k=0;k<18;k++)for(unsigned i=0;i<1088;i++){auto next=[&](){seed=seed*UINT64_C(6364136223846793005)+1;return seed;};uint64_t a=i<64?edges[i/8]:next(),b=i<64?edges[i%8]:next();
 for(unsigned ca=0;ca<2;ca++)for(unsigned so=0;so<2;so++){PPCContext c{};alignas(32)uint8_t mem[32]{};c.r3.u64=123;c.r4.u64=a;c.r5.u64=b;c.xer.ca=ca;c.xer.so=so;c.xer.ov=1;c.cr0.lt=1;c.cr0.gt=0;c.cr0.eq=1;c.cr0.so=!so;c.cr1.lt=1;
 unsigned kind=k/6;bool record=k%6>=3;unsigned dest=3+k%3;
 uint64_t left=kind==1?~a:a,right=kind==0?b:(kind==2?UINT64_MAX:0);unsigned input=kind==0?0:ca;
 unsigned expectedCA,ignored;serial(uint32_t(left),uint32_t(right),input,32,expectedCA);uint64_t expected=serial(left,right,input,64,ignored);
 funcs[k](c,mem);uint64_t actual=dest==3?c.r3.u64:(dest==4?c.r4.u64:c.r5.u64);
 if(actual!=expected||c.xer.ca!=expectedCA||c.xer.so!=so||c.xer.ov!=1||c.cr1.lt!=1)return 1;
 if((dest!=4&&c.r4.u64!=a)||(dest!=5&&c.r5.u64!=b)||(dest!=3&&c.r3.u64!=123))return 2;
 if(record){uint32_t low=uint32_t(expected);if(c.cr0.lt!=(low>>31)||c.cr0.gt!=(!(low>>31)&&low!=0)||c.cr0.eq!=(low==0)||c.cr0.so!=so)return 3;}
 else if(c.cr0.lt!=1||c.cr0.gt!=0||c.cr0.eq!=1||c.cr0.so!=!so)return 4;++checks;
 }}std::printf("carry arithmetic: %u native cases passed; guest32 CA/CR0 policy\n",checks);}
'''.replace('FUNCTIONS',','.join('carry_%X'%(0x1000+i*8) for i in range(18)))
    (work/'native.cpp').write_text(harness)
    run([args.clang.absolute(),'-std=c++20','-O2','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(upstream/'XenonUtils'),'-I'+str(upstream/'thirdparty/simde'),work/'native.cpp','-o',work/'native',*(['-fno-sanitize-link-runtime','-lubsan'] if args.system_ubsan else [])])
    result=run([work/'native']);assert '78336 native cases passed' in result
    report={'scope':'synthetic_upstream_generated_host_guest32_CA_CR0_only','cases':78336,'OE_variants_rejected':6,'host':platform.machine(),'compiler':run([args.clang.absolute(),'--version']).splitlines()[0],'binary_sha256':hashlib.sha256(args.recompiler.read_bytes()).hexdigest(),'patch_sha256':hashlib.sha256((ROOT/'tools/recompilation/patches/0005-carry-arithmetic.patch').read_bytes()).hexdigest(),'game_executed':False,'result':result.strip()}
    (work/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
