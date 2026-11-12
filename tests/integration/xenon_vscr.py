#!/usr/bin/env python3
"""Own synthetic vectors for VSCR SAT/NJ, integer saturation and signed fixed conversion."""
import argparse
import hashlib
import json
import platform
import struct
from pathlib import Path
from xenon_eqv import ROOT,run
from xenon_single_update import elf

OPS=[(4,832),(4,512),(4,640),(4,1920),(4,1536),(4,270),(5,576),(5,640)]


def vx128(primary,xo,vd,va,vb):
    return primary<<26|(vd&31)<<21|(va&31)<<16|(vb&31)<<11|((va>>6)&1)<<10|((va>>5)&1)<<5|((vd>>5)&3)<<2|((vb>>5)&3)|xo


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('upstream','recompiler','clang','work'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--system-ubsan',action='store_true');args=p.parse_args();work=args.work.resolve();upstream=args.upstream.resolve()
    if not work.is_relative_to(ROOT/'build') or work.exists():p.error('--work must be new and under build/')
    bodies={};rows=[];code=b''
    for kind,(primary,xo) in enumerate(OPS):
        a,b=(65,95) if primary==5 else (5,6)
        for alias in range(3):
            dest=(64,a,b)[alias] if primary==5 else (4,a,b)[alias]
            word=vx128(primary,xo,dest,a,b) if primary==5 else primary<<26|dest<<21|a<<16|b<<11|xo
            code+=struct.pack('>II',word,0x4e800020);rows.append('{%d,%d,%d,%d}'%(kind,dest,a,b))
    bodies['sat']=code;code=b''
    for scale in range(32):
        for primary,dest,src in ((4,4,5),(4,5,5),(6,64,65),(6,65,65)):
            word=primary<<26|(dest&31)<<21|scale<<16|(src&31)<<11|(970 if primary==4 else 560|((dest>>5)&3)<<2|((src>>5)&3))
            code+=struct.pack('>II',word,0x4e800020)
    bodies['convert']=code
    mt=4<<26|5<<11|1604;mf4=4<<26|4<<21|1540;mf8=4<<26|8<<21|1540;add=4<<26|4<<21|6<<16|7<<11|10
    bodies['state']=struct.pack('>7I',mt,mf4,0x4e800020,mt,add,mf8,0x4e800020)
    for name,body in bodies.items():
        src,dst=work/name/'input',work/name/'output';src.mkdir(parents=True);dst.mkdir()
        (src/(name+'.o')).write_bytes(elf(body));log=run([args.recompiler.resolve(),src,dst]);(work/name/'generation.log').write_text(log)
        if any(s in log for s in ('Unrecognized instruction','unimplemented','no comparison','Unable to decode')):raise RuntimeError('Incomplete VSCR generation: '+log)
    harness=r'''
#include "sat/output/sat.cpp"
#include "convert/output/convert.cpp"
#include "state/output/state.cpp"
#include <array>
#include <cstdio>
#include <cmath>
#include <cstring>
struct Op{unsigned kind,dest,a,b;};const std::array<Op,24> ops{{ROWS}};
using Fn=void(*)(PPCContext&,uint8_t*);const std::array<Fn,24> satFns{SAT_FUNCTIONS};const std::array<Fn,128> convertFns{CONVERT_FUNCTIONS};
PPCVRegister& vr(PPCContext& c,unsigned n){switch(n){case 4:return c.v4;case 5:return c.v5;case 6:return c.v6;case 64:return c.v64;case 65:return c.v65;default:return c.v95;}}
int64_t clamp(int64_t value,int64_t lo,int64_t hi,bool& sat){if(value<lo){sat=true;return lo;}if(value>hi){sat=true;return hi;}return value;}
void flags(PPCContext& c){c.r3.u64=123;c.cr0.lt=1;c.cr0.eq=1;c.xer.ca=1;c.xer.so=1;}
bool preserved(PPCContext& c){return c.r3.u64==123&&c.cr0.lt==1&&c.cr0.eq==1&&c.xer.ca==1&&c.xer.so==1;}
int32_t refConvert(uint32_t bits,unsigned scale,bool& sat){
 if((bits&0x7fffffff)>0x7f800000)return 0;
 float source;std::memcpy(&source,&bits,4);long double value=std::ldexp(static_cast<long double>(source),int(scale));
 if(value>2147483647.0L){sat=true;return INT32_MAX;}if(value<-2147483648.0L){sat=true;return INT32_MIN;}
 return int32_t(std::trunc(value));
}
int main(){unsigned intChecks=0,conversionChecks=0,stateChecks=0;uint64_t seed=91;
 const std::array<int32_t,10> edges{-32768,-129,-1,0,1,127,128,255,256,32767};
 const std::array<int32_t,9> wide{INT32_MIN,-32769,-32768,-1,0,1,32767,32768,INT32_MAX};
 auto next=[&](){seed=seed*UINT64_C(6364136223846793005)+1;return uint32_t(seed>>32);};
 for(unsigned k=0;k<24;k++)for(unsigned i=0;i<256;i++)for(unsigned initial:{0u,1u,0x10000u,0x10001u}){
  PPCContext c{};alignas(32)uint8_t memory[32]{};auto op=ops[k];PPCVRegister a{},b{},expected{};bool saturated=false;
  if(op.kind==0||op.kind==5||op.kind==6){for(unsigned lane=0;lane<8;lane++){a.s16[lane]=i<100?int16_t(edges[(i/10+lane)%10]):int16_t(next());b.s16[lane]=i<100?int16_t(edges[(i%10+lane)%10]):int16_t(next());}}
  else if(op.kind==1||op.kind==4){for(unsigned lane=0;lane<16;lane++){a.u8[lane]=uint8_t(i<64?i*4+lane:next());b.u8[lane]=uint8_t(i<64?255-i*4-lane:next());}}
  else {for(unsigned lane=0;lane<4;lane++){a.s32[lane]=i<81?wide[(i/9+lane)%9]:int32_t(next());b.s32[lane]=i<81?wide[(i%9+lane)%9]:int32_t(next());}}
  if(op.kind==0)for(unsigned lane=0;lane<8;lane++)expected.s16[lane]=int16_t(clamp(int64_t(a.s16[lane])+b.s16[lane],-32768,32767,saturated));
  if(op.kind==1)for(unsigned lane=0;lane<16;lane++)expected.u8[lane]=uint8_t(clamp(int64_t(a.u8[lane])+b.u8[lane],0,255,saturated));
  if(op.kind==2)for(unsigned lane=0;lane<4;lane++)expected.u32[lane]=uint32_t(clamp(int64_t(uint64_t(a.u32[lane]))+b.u32[lane],0,INT64_C(4294967295),saturated));
  if(op.kind==3)for(unsigned lane=0;lane<4;lane++)expected.s32[lane]=int32_t(clamp(int64_t(a.s32[lane])-b.s32[lane],INT32_MIN,INT32_MAX,saturated));
  if(op.kind==4)for(unsigned lane=0;lane<16;lane++)expected.u8[lane]=uint8_t(clamp(int64_t(a.u8[lane])-b.u8[lane],0,255,saturated));
  if(op.kind==5||op.kind==6)for(unsigned lane=0;lane<8;lane++){expected.u8[lane]=uint8_t(clamp(b.s16[lane],0,255,saturated));expected.u8[lane+8]=uint8_t(clamp(a.s16[lane],0,255,saturated));}
  if(op.kind==7)for(unsigned lane=0;lane<4;lane++){expected.s16[lane]=int16_t(clamp(b.s32[lane],-32768,32767,saturated));expected.s16[lane+4]=int16_t(clamp(a.s32[lane],-32768,32767,saturated));}
  vr(c,op.a)=a;vr(c,op.b)=b;c.vscr.write(initial);flags(c);satFns[k](c,memory);
  if(std::memcmp(&vr(c,op.dest),&expected,16)||c.vscr.read()!=(initial|unsigned(saturated))||!preserved(c))return 1;
  if((op.dest!=op.a&&std::memcmp(&vr(c,op.a),&a,16))||(op.dest!=op.b&&std::memcmp(&vr(c,op.b),&b,16)))return 2;
  ++intChecks;
 }
 const std::array<uint32_t,24> input{0,0x80000000,0x3f800000,0xbf800000,1,0x80000001,0x007fffff,0x807fffff,0x00800000,0x80800000,0x4effffff,0xceffffff,0x4f000000,0xcf000000,0x4f000001,0xcf000001,0x7f800000,0xff800000,0x7fc00001,0xffc00001,0x7f800001,0xff800001,0x3fc00000,0x7f7fffff};
 for(unsigned k=0;k<128;k++)for(unsigned i=0;i<280;i++)for(unsigned initial:{0u,1u,0x10000u,0x10001u}){
  unsigned scale=k/4,mode=k%4,source=mode<2?5:65,dest=mode==0?4:(mode==1?5:(mode==2?64:65));PPCContext c{};alignas(32)uint8_t memory[32]{};PPCVRegister original{},expected{};bool saturated=false;
  for(unsigned lane=0;lane<4;lane++){original.u32[lane]=i<24?input[i]:next();expected.s32[lane]=refConvert(original.u32[lane],scale,saturated);}
  vr(c,source)=original;c.vscr.write(initial);flags(c);convertFns[k](c,memory);
  if(std::memcmp(&vr(c,dest),&expected,16)||c.vscr.read()!=(initial|unsigned(saturated))||!preserved(c))return 3;
  if(dest!=source&&std::memcmp(&vr(c,source),&original,16))return 4;++conversionChecks;
 }
 for(unsigned bits:{0u,1u,0x10000u,0x10001u,0xffffffffu}){
  PPCContext c{};alignas(32)uint8_t memory[32]{};c.vscr.write(0x10001);c.v5.u32[0]=bits;state_1000(c,memory);
  if(c.vscr.read()!=(bits&0x10001u)||c.v4.u32[0]!=(bits&0x10001u)||c.v4.u32[1]||c.v4.u32[2]||c.v4.u32[3])return 5;++stateChecks;
  c.fpscr.loadFromHost();for(unsigned lane=0;lane<4;lane++){c.v6.u32[lane]=1;c.v7.u32[lane]=0;}state_100C(c,memory);
  for(unsigned lane=0;lane<4;lane++)if(c.v4.u32[lane]!=((bits&0x10000u)?0u:1u))return 6;
  if(c.v8.u32[0]!=(bits&0x10001u))return 7;++stateChecks;
  uint32_t before=c.vscr.read();bool caught=false;try{c.vscr.signedFixed(0,32);}catch(const std::out_of_range& e){caught=std::strcmp(e.what(),"VSCR_FIXED_SCALE_OUT_OF_RANGE")==0;}
  if(!caught||c.vscr.read()!=before)return 8;++stateChecks;
 }
 std::printf("VSCR: integer=%u conversion=%u state=%u native cases passed\n",intChecks,conversionChecks,stateChecks);
}
'''.replace('ROWS',','.join(rows)).replace('SAT_FUNCTIONS',','.join('sat_%X'%(0x1000+i*8) for i in range(24))).replace('CONVERT_FUNCTIONS',','.join('convert_%X'%(0x1000+i*8) for i in range(128)))
    (work/'native.cpp').write_text(harness);run([args.clang.absolute(),'-std=c++20','-O2','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(upstream/'XenonUtils'),'-I'+str(upstream/'thirdparty/simde'),work/'native.cpp','-o',work/'native',*(['-fno-sanitize-link-runtime','-lubsan'] if args.system_ubsan else [])]);result=run([work/'native']);assert 'integer=24576 conversion=143360 state=15 native cases passed' in result
    report={'scope':'synthetic_upstream_generated_host_VSCR_SAT_NJ_and_conversion','cases':167951,'integer_cases':24576,'conversion_cases':143360,'state_cases':15,'host':platform.machine(),'compiler':run([args.clang.absolute(),'--version']).splitlines()[0],'binary_sha256':hashlib.sha256(args.recompiler.read_bytes()).hexdigest(),'context_sha256':hashlib.sha256((upstream/'XenonUtils/ppc_context.h').read_bytes()).hexdigest(),'patch_sha256':hashlib.sha256((ROOT/'tools/recompilation/patches/0010-vscr-saturation.patch').read_bytes()).hexdigest(),'game_executed':False,'result':result.strip()}
    (work/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
