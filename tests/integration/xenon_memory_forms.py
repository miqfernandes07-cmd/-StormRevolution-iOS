#!/usr/bin/env python3
"""Explicit native tests for 14 experimental memory opcodes, using own ELF fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import struct
from xenon_eqv import ROOT, run
from xenon_single_update import elf

# name, primary opcode, XO (None=D form), width, store, floating, signed, update
OPS = [
 ('lhzu',41,None,2,0,0,0,1),('lhau',43,None,2,0,0,1,1),('sthu',45,None,2,1,0,0,1),
 ('lwzux',31,55,4,0,0,0,1),('lbzux',31,119,1,0,0,0,1),('sthux',31,439,2,1,0,0,1),
 ('lhzux',31,311,2,0,0,0,1),('ldux',31,53,8,0,0,0,1),('stdux',31,181,8,1,0,0,1),
 ('lfdu',51,None,8,0,1,0,1),('stfdu',55,None,8,1,1,0,1),('lfsux',31,567,4,0,1,0,1),
 ('stfsux',31,695,4,1,1,0,1),('lhbrx',31,790,2,0,0,0,0)]


def encode(op, rt=4, ra=3, rb=5, offset=-8):
    _, primary, xo, *_ = op
    return primary<<26 | rt<<21 | ra<<16 | ((rb<<11 | xo<<1) if xo is not None else (offset&65535))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('upstream','recompiler','clang','work'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--system-ubsan',action='store_true');args=parser.parse_args()
    work, upstream=args.work.resolve(),args.upstream.resolve()
    if not work.is_relative_to(ROOT/'build') or work.exists(): parser.error('--work must be new and under build/')
    code=b'';rows=[];invalid=b'';invalid_count=0
    for op in OPS:
        name,primary,xo,width,store,fp,sign,update=op
        for variant in range(3):
            rt=3 if store and not fp and variant==1 else 4
            ra=0 if not update and variant==2 else 3
            rb=4 if xo is not None and variant==1 and not store else (3 if xo is not None and variant==2 and update else 5)
            offset=(-8,8,-32768)[variant]
            rows.append('{%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d}'%(width,store,fp,sign,update,name=='lhbrx',xo is not None,rt,ra,rb,offset,variant))
            code+=struct.pack('>II',encode(op,rt,ra,rb,offset),0x4e800020)
        if update:
            invalid+=struct.pack('>II',encode(op,ra=0),0x4e800020);invalid_count+=1
            if not fp and not store:
                invalid+=struct.pack('>II',encode(op,rt=3),0x4e800020);invalid_count+=1
            if store:
                invalid+=struct.pack('>III',encode(op),0x7c0006ac,0x4e800020);invalid_count+=1
    for name,body in (('valid',code),('invalid',invalid)):
        src,dst=work/name/'input',work/name/'output';src.mkdir(parents=True);dst.mkdir()
        (src/'memory.o').write_bytes(elf(body))
        log=run([args.recompiler.resolve(),src,dst]);(work/name/'generation.log').write_text(log)
        if name=='valid' and ('Unrecognized instruction' in log or 'unimplemented' in log): raise RuntimeError('Incomplete memory generation')
        if name=='invalid' and log.count('Unrecognized instruction')!=invalid_count: raise RuntimeError('Invalid memory forms not rejected: '+log)
    harness=r'''
#include <cstdint>
#include <array>
#include <cstdio>
#include <cmath>
struct Fault{};bool fail=false;
uint64_t read(uint8_t*b,uint32_t a,unsigned n){if(fail||a>65568-n||a%n)throw Fault{};uint64_t v=0;for(unsigned i=0;i<n;i++)v=(v<<8)|b[a+i];return v;}
void write(uint8_t*b,uint32_t a,uint64_t v,unsigned n){if(fail||a>65568-n||a%n)throw Fault{};for(unsigned i=0;i<n;i++)b[a+i]=uint8_t(v>>(8*(n-1-i)));}
#ifndef DEFAULT_MEMORY
#define PPC_LOAD_U8(a) read(base,uint32_t(a),1)
#define PPC_LOAD_U16(a) read(base,uint32_t(a),2)
#define PPC_LOAD_U32(a) read(base,uint32_t(a),4)
#define PPC_LOAD_U64(a) read(base,uint32_t(a),8)
#define PPC_STORE_U16(a,v) write(base,uint32_t(a),v,2)
#define PPC_STORE_U32(a,v) write(base,uint32_t(a),v,4)
#define PPC_STORE_U64(a,v) write(base,uint32_t(a),v,8)
#endif
#include "valid/output/memory.cpp"
struct Op{unsigned width;bool store,fp,sign,update,reverse,indexed;unsigned rt,ra,rb;int offset;unsigned variant;};
const std::array<Op,42> ops{{ROWS}};
using Fn=void(*)(PPCContext&,uint8_t*);const std::array<Fn,42> funcs{FUNCTIONS};
uint64_t widen(uint32_t x){uint64_t sign=uint64_t(x>>31)<<63;unsigned e=x>>23&255,m=x&0x7fffff;
 if(e==255)return sign|UINT64_C(0x7ff0000000000000);if(e)return sign|(uint64_t(e+896)<<52)|(uint64_t(m)<<29);
 if(!m)return sign;int v=-126;while(!(m&0x800000)){m<<=1;--v;}return sign|(uint64_t(v+1023)<<52)|(uint64_t(m&0x7fffff)<<29);}
uint64_t& reg(PPCContext& c,unsigned n){switch(n){case 0:return c.r0.u64;case 3:return c.r3.u64;case 4:return c.r4.u64;default:return c.r5.u64;}}
uint64_t& freg(PPCContext& c,unsigned n){return n==3?c.f3.u64:c.f4.u64;}
int main(){unsigned checks=0;const std::array<uint64_t,9> values{0,1,0x7fff,0x8000,0xffff,UINT64_C(0x8000000000000000),UINT64_MAX,UINT64_C(0x0123456789abcdef),UINT64_C(0x3fc00000)};
 for(unsigned k=0;k<ops.size();k++){auto op=ops[k];for(uint32_t ea:{0u,16u,65536u})for(auto value:values){
  alignas(32)std::array<uint8_t,65568> memory;memory.fill(0xa5);PPCContext c{};
  c.r0.u64=999;c.r3.u64=17;c.r4.u64=value;c.r5.u64=18;freg(c,op.rt)=op.fp&&op.store&&op.width==4?UINT64_C(0x3ff8000000000000):value;
  if(op.indexed){if(!op.ra)reg(c,op.rb)=ea;else if(op.ra==op.rb)reg(c,op.ra)=UINT64_C(0x1234000000000000)|(ea/2);else{reg(c,op.ra)=UINT64_C(0x1234000000000000)|uint32_t(ea-8);reg(c,op.rb)=8;}}
  else reg(c,op.ra)=UINT64_C(0x1234000000000000)|uint32_t(ea-op.offset);
  const uint64_t oldRa=reg(c,op.ra),source=op.fp?freg(c,op.rt):reg(c,op.rt);
  c.cr0.lt=1;c.cr0.eq=1;c.xer.ca=1;c.xer.so=1;
  if(!op.store)write(memory.data(),ea,value,op.width);auto expected=memory;
  funcs[k](c,memory.data());
  if(reg(c,op.ra)!=(op.update?ea:oldRa)||c.r0.u64!=999||c.cr0.lt!=1||c.cr0.eq!=1||c.xer.ca!=1||c.xer.so!=1)return 1;
  if(op.store){write(expected.data(),ea,op.fp&&op.width==4?0x3fc00000:source,op.width);if(memory!=expected)return 2;if(op.fp&&freg(c,op.rt)!=source)return 3;}
  else{uint64_t want=value;if(op.width<8)want&=(UINT64_C(1)<<(op.width*8))-1;
   if(op.reverse)want=((want&255)<<8)|(want>>8);
   if(op.sign&&want&0x8000)want|=UINT64_C(0xffffffffffff0000);
   if(op.fp&&op.width==4){uint32_t bits=uint32_t(value);if((bits&0x7fffffff)>0x7f800000){if(!std::isnan(c.f4.f64))return 4;want=freg(c,op.rt);}else want=widen(bits);}
   if((op.fp?freg(c,op.rt):reg(c,op.rt))!=want||memory!=expected)return 5;
  }++checks;
#ifndef DEFAULT_MEMORY
  // Re-run with a refused access, observing RA/destination and all RAM.
  PPCContext previous=c;auto original=memory;fail=true;bool caught=false;
  try{funcs[k](c,memory.data());}catch(const Fault&){caught=true;}fail=false;
  if(!caught||reg(c,op.ra)!=reg(previous,op.ra)||reg(c,op.rt)!=reg(previous,op.rt)||freg(c,op.rt)!=freg(previous,op.rt)||memory!=original)return 6;++checks;
#endif
 }}std::printf("memory forms: %u native cases passed\n",checks);}
'''.replace('ROWS',','.join(rows)).replace('FUNCTIONS',','.join('memory_%X'%(0x1000+i*8) for i in range(42)))
    (work/'native.cpp').write_text(harness);results={}
    for mode,flags,count in (('default',['-DDEFAULT_MEMORY'],1134),('checked',[],2268)):
        run([args.clang.absolute(),'-std=c++20','-O2','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(upstream/'XenonUtils'),'-I'+str(upstream/'thirdparty/simde'),work/'native.cpp','-o',work/mode,*flags,*(['-fno-sanitize-link-runtime','-lubsan'] if args.system_ubsan else [])])
        result=run([work/mode]);assert f'{count} native cases passed' in result;results[mode]=result.strip()
    report={'scope':'synthetic_upstream_generated_host_guest32_memory_only','opcodes':14,'cases':3402,'invalid_rejections':invalid_count,'host':platform.machine(),'compiler':run([args.clang.absolute(),'--version']).splitlines()[0],'binary_sha256':hashlib.sha256(args.recompiler.read_bytes()).hexdigest(),'patch_sha256':hashlib.sha256((ROOT/'tools/recompilation/patches/0003-memory-forms.patch').read_bytes()).hexdigest(),'game_executed':False,'results':results}
    (work/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
