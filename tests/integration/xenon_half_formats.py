#!/usr/bin/env python3
"""Synthetic VMX128 D3D binary16 pack/unpack, host native execution with UBSan."""
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
    p.add_argument('--system-ubsan',action='store_true');a=p.parse_args();w=a.work.resolve();u=a.upstream.resolve()
    if not w.is_relative_to(ROOT/'build') or w.exists():p.error('--work must be new under build/')
    rows=[];code=b''
    for kind in (3,5):
        for mask in (1,2,3):
            for shift in range(4):
                for source,destination in ((5,4),(5,5),(95,64),(95,95)):
                    imm=kind*4+mask
                    word=0x18000610|(destination&31)<<21|imm<<16|(source&31)<<11|shift<<6|(destination>>5)<<2|(source>>5)
                    rows.append('{%d,%d,%d,%d,%d}'%(kind,mask,shift,source,destination));code+=struct.pack('>II',word,0x4e800020)
    for kind in (3,5):
        for source,destination in ((5,4),(5,5),(95,64),(95,95)):
            word=0x180007f0|(destination&31)<<21|(kind*4)<<16|(source&31)<<11|(destination>>5)<<2|(source>>5)
            rows.append('{%d,0,0,%d,%d}'%(kind,source,destination));code+=struct.pack('>II',word,0x4e800020)
    src,dst=w/'input',w/'output';src.mkdir(parents=True);dst.mkdir();(src/'half.o').write_bytes(elf(code))
    log=run([a.recompiler.resolve(),src,dst]);(w/'generation.log').write_text(log)
    if any(x in log for x in ('Unrecognized','Unexpected','Unable to decode','unimplemented')):raise RuntimeError(log)
    harness=r'''
#include "output/half.cpp"
#include <array>
#include <cmath>
#include <cstdio>
#include <cstring>
struct Op{unsigned kind,mask,shift,source,dest;};const std::array<Op,104> ops{{ROWS}};
using Fn=void(*)(PPCContext&,uint8_t*);const std::array<Fn,104> functions{FUNCTIONS};
PPCVRegister& vr(PPCContext& c,unsigned n){switch(n){case 4:return c.v4;case 5:return c.v5;case 64:return c.v64;default:return c.v95;}}
uint32_t floatBits(float x){uint32_t b;std::memcpy(&b,&x,4);return b;}
uint32_t unpack(uint16_t h){unsigned e=(h>>10)&31,m=h&1023;uint32_t sign=uint32_t(h&0x8000)<<16;
 if(e==31)return sign|0x7f800000u|(m?(m<<13)|0x400000u:0);
 double x=e?std::ldexp(1.0+double(m)/1024.0,int(e)-15):std::ldexp(double(m),-24);
 return sign|floatBits(float(x));}
uint16_t pack(uint32_t b){uint16_t sign=uint16_t((b>>16)&0x8000);unsigned e=(b>>23)&255,m=b&0x7fffff;
 if(e==255)return uint16_t(sign|0x7c00|(m?0x200|(m>>13):0));
 float x;uint32_t mag=b&0x7fffffff;std::memcpy(&x,&mag,4);double v=x;
 if(v>=65504.0)return uint16_t(sign|0x7bff);
 if(v<std::ldexp(1.0,-14))return uint16_t(sign|unsigned(std::floor(std::ldexp(v,24))));
 int power=0;double mantissa=std::frexp(v,&power);unsigned fraction=unsigned(std::floor((mantissa*2-1)*1024));
 return uint16_t(sign|unsigned(power+14)<<10|fraction);}
int main(){uint64_t checks=0,seed=127;auto next=[&](){seed=seed*UINT64_C(6364136223846793005)+1;return uint32_t(seed>>32);};
 for(unsigned h=0;h<65536;h++){uint32_t b=unpack(uint16_t(h));if(PPCHalfBitsToFloat32(uint16_t(h))!=b)return 1;
  if(PPCFloat32ToHalfBits(b)!=pack(b))return 2;checks+=2;}
 const std::array<uint32_t,28> edges{0,0x80000000,1,0x80000001,0x33000000,0x337fffff,0x33800000,0x33800001,0x387fffff,0x38800000,0x38800001,0x3f800000,0xbf800000,0x477fdfff,0x477fe000,0x477fffff,0x47800000,0xc7800000,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7f800001,0xff800001,0x7fc00001,0xffc00001,0x3eaaaaab,0xbeaaaaab};
 for(unsigned i=0;i<100028;i++){uint32_t b=i<edges.size()?edges[i]:next();if(PPCFloat32ToHalfBits(b)!=pack(b))return 3;++checks;}
 for(unsigned k=0;k<104;k++){auto op=ops[k];unsigned count=op.mask?256:16384;
  for(unsigned i=0;i<count;i++){PPCContext c{};alignas(32)uint8_t memory[32]{};PPCVRegister source{},expected{},temp{};
   for(unsigned lane=0;lane<4;lane++)source.u32[lane]=i<edges.size()?edges[(i+lane)%edges.size()]:next();
   if(!op.mask)for(unsigned lane=0;lane<8;lane++)source.u16[lane]=uint16_t(i*4+lane%4);
   vr(c,op.source)=source;if(op.dest!=op.source)for(unsigned lane=0;lane<4;lane++)vr(c,op.dest).u32[lane]=0xcdcdcdcdu;
   expected=vr(c,op.dest);
   if(op.mask){if(op.kind==3)temp.u32[0]=uint32_t(pack(source.u32[3]))<<16|pack(source.u32[2]);
    else for(unsigned lane=0;lane<4;lane++)temp.u16[lane]=pack(source.u32[lane]);
    if(op.mask==1)expected.u32[op.shift]=temp.u32[0];
    else if(op.mask==3&&op.shift==3)expected.u32[0]=temp.u32[1];
    else {expected.u32[op.shift]=temp.u32[0];expected.u32[(op.shift+1)%4]=temp.u32[1];}}
   else if(op.kind==3){expected.u32[3]=unpack(source.u16[1]);expected.u32[2]=unpack(source.u16[0]);expected.u32[1]=0;expected.u32[0]=0x3f800000;}
   else for(unsigned lane=0;lane<4;lane++)expected.u32[lane]=unpack(source.u16[lane]);
   c.vscr.write(0x10001);c.r3.u64=321;c.cr0.eq=1;functions[k](c,memory);
   if(std::memcmp(&vr(c,op.dest),&expected,16)||c.vscr.read()!=0x10001||c.r3.u64!=321||!c.cr0.eq){std::fprintf(stderr,"operation %u vector %u failed\n",k,i);return 4;}
   if(op.source!=op.dest&&std::memcmp(&vr(c,op.source),&source,16))return 5;++checks;
  }}
 std::printf("D3D half: %llu native checks passed\n",(unsigned long long)checks);
}
'''.replace('ROWS',','.join(rows)).replace('FUNCTIONS',','.join('half_%X'%(0x1000+i*8) for i in range(104)))
    (w/'native.cpp').write_text(harness)
    run([a.clang.absolute(),'-std=c++20','-O2','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(u/'XenonUtils'),'-I'+str(u/'thirdparty/simde'),w/'native.cpp','-o',w/'native',*(['-fno-sanitize-link-runtime','-lubsan'] if a.system_ubsan else [])])
    result=run([w/'native']);assert '386748 native checks passed' in result
    report={'scope':'synthetic_D3D_binary16_pack_unpack','checks':386748,'host':platform.machine(),'binary_sha256':hashlib.sha256(a.recompiler.read_bytes()).hexdigest(),'context_sha256':hashlib.sha256((u/'XenonUtils/ppc_context.h').read_bytes()).hexdigest(),'game_executed':False,'result':result.strip()}
    (w/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
