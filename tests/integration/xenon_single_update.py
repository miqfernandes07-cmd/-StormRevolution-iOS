#!/usr/bin/env python3
"""Explicit host integration for experimental LFSU/STFSU, with synthetic ELF only."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import struct
from xenon_eqv import ROOT, run

OFFSETS = (0, 4, -4, 32764, -32768)


def elf(code):
    names = b'\0.text\0.shstrtab\0'
    table = (52 + len(code) + len(names) + 3) & ~3
    header = struct.pack('>16sHHIIIIIHHHHHH', b'\x7fELF\x01\x02\x01' + bytes(9),
                         1, 20, 1, 0x1000, 0, table, 0, 52, 0, 0, 40, 3, 2)
    body = (header + code + names).ljust(table, b'\0')
    return body + bytes(40) + struct.pack('>10I', 1, 1, 6, 0x1000, 52, len(code), 0, 0, 4, 0) + struct.pack('>10I', 7, 3, 0, 0x1000 + ((len(code) + 4095) & ~4095), 52+len(code), len(names), 0, 0, 1, 0)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('upstream', 'recompiler', 'clang', 'work'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--system-ubsan', action='store_true')
    args = p.parse_args()
    work, upstream = args.work.resolve(), args.upstream.resolve()
    if not work.is_relative_to(ROOT / 'build') or work.exists():
        p.error('--work must be a new directory under build/')
    for name, invalid in (('valid', False), ('invalid', True)):
        src, dst = work/name/'input', work/name/'output'
        src.mkdir(parents=True); dst.mkdir()
        code = b''
        for offset in ((4,) if invalid else OFFSETS):
            for opcode in (49, 53):
                code += struct.pack('>II', opcode << 26 | 1 << 21 | (0 if invalid else 3) << 16 | (offset & 65535), 0x4e800020)
        # Explicitly unsupported MMIO sequence: stfsu ; eieio ; blr.
        if invalid:
            code += struct.pack('>III', 53 << 26 | 1 << 21 | 3 << 16 | 4, 0x7c0006ac, 0x4e800020)
        (src/'memory.o').write_bytes(elf(code))
        log = run([args.recompiler.resolve(), src, dst])
        (work/name/'generation.log').write_text(log)
        if invalid:
            if log.count('Unrecognized instruction') != 3:
                raise RuntimeError('RA=0 and MMIO forms must remain explicitly rejected')
        elif 'Unrecognized instruction' in log or 'unimplemented' in log:
            raise RuntimeError('LFSU/STFSU generation is incomplete')
    harness = r'''
#include <cstdint>
#include <cstring>
#include <array>
#include <cmath>
#include <cfenv>
#include <cstdio>
struct Fault {};
static bool forceFault=false;
uint32_t load(uint8_t* base,uint32_t ea) {
  if(forceFault||ea>65564||ea%4) throw Fault{};
  return uint32_t(base[ea])*16777216u+uint32_t(base[ea+1])*65536u+uint32_t(base[ea+2])*256u+base[ea+3];
}
void store(uint8_t* base,uint32_t ea,uint32_t bits) {
  if(forceFault||ea>65564||ea%4) throw Fault{};
  for(unsigned i=0;i<4;i++) base[ea+i]=uint8_t(bits>>(24-i*8));
}
#ifndef STORM_DEFAULT_MEMORY
#define PPC_LOAD_U32(x) load(base,uint32_t(x))
#define PPC_STORE_U32(x,y) store(base,uint32_t(x),y)
#endif
#include "valid/output/memory.cpp"
using Fn=void(*)(PPCContext&,uint8_t*);
const std::array<Fn,10> functions{FUNCTIONS};
uint64_t widen(uint32_t bits) {
  uint64_t sign=uint64_t(bits>>31)<<63; unsigned exp=(bits>>23)&255,m=bits&0x7fffff;
  if(exp==255) return sign|UINT64_C(0x7ff0000000000000);
  if(exp) return sign|(uint64_t(exp+896)<<52)|(uint64_t(m)<<29);
  if(!m) return sign;
  int e=-126;while(!(m&0x800000)){m<<=1;--e;}
  return sign|(uint64_t(e+1023)<<52)|(uint64_t(m&0x7fffff)<<29);
}
int main() {
  if(std::fesetround(FE_TONEAREST)) return 2;
  unsigned checks=0;
  const std::array<int,5> offsets{0,4,-4,32764,-32768};
  const std::array<uint32_t,12> inputs{0,0x80000000,0x3f800000,0xc0200000,0x00800000,1,
     0x80000001,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc00001};
  const std::array<std::array<uint64_t,2>,15> pairs{{
    {0,0},{UINT64_C(0x8000000000000000),0x80000000},{UINT64_C(0x3ff0000000000000),0x3f800000},
    {UINT64_C(0xc004000000000000),0xc0200000},{UINT64_C(0x3ff0000010000000),0x3f800000},
    {UINT64_C(0x3ff0000030000000),0x3f800002},{UINT64_C(0x3810000000000000),0x00800000},
    {UINT64_C(0x36a0000000000000),1},{UINT64_C(0x3690000000000000),0},
    {UINT64_C(0x47efffffe0000000),0x7f7fffff},{UINT64_C(0x47f0000000000000),0x7f800000},
    {UINT64_C(0x7ff0000000000000),0x7f800000},{UINT64_C(0xfff0000000000000),0xff800000},
    {UINT64_C(0x7ff8000000000001),0x7fc00000},{UINT64_C(0x8000000000000001),0x80000000}}};
  for(unsigned variant=0;variant<10;variant++) for(uint32_t ea: {0u,16u,65536u}) {
    bool isStore=variant%2; unsigned count=isStore?pairs.size():inputs.size();
    for(unsigned i=0;i<count;i++) {
      alignas(32) std::array<uint8_t,65568> memory; memory.fill(0xa5);
      PPCContext ctx{};ctx.r3.u64=UINT64_C(0x1234000000000000)|uint32_t(ea-offsets[variant/2]);
      ctx.r4.u64=17;ctx.f1.u64=isStore?pairs[i][0]:UINT64_C(0x123456789abcdef0);
      ctx.cr0.lt=1;ctx.cr0.eq=1;ctx.xer.ca=1;ctx.xer.so=1;
      uint32_t bits=isStore?uint32_t(pairs[i][1]):inputs[i];
      if(!isStore) store(memory.data(),ea,bits);
      auto before=memory;
      functions[variant](ctx,memory.data());
      if(ctx.r3.u64!=ea||ctx.r4.u64!=17||ctx.cr0.lt!=1||ctx.cr0.eq!=1||ctx.xer.ca!=1||ctx.xer.so!=1) return 3;
      if(isStore) {
        auto expected=before;store(expected.data(),ea,bits);
        bool nan=(pairs[i][0]&UINT64_C(0x7fffffffffffffff))>UINT64_C(0x7ff0000000000000);
        if(nan) {uint32_t actual=load(memory.data(),ea);if((actual&0x7f800000)!=0x7f800000||!(actual&0x7fffff)) return 4;
          for(unsigned b=0;b<4;b++)expected[ea+b]=memory[ea+b];}
        if(memory!=expected||ctx.f1.u64!=pairs[i][0])return 5;
      } else {
        bool nan=(bits&0x7fffffff)>0x7f800000;
        if((nan?!std::isnan(ctx.f1.f64):ctx.f1.u64!=widen(bits))||memory!=before) return 6;
      }
      ++checks;
    }
#ifndef STORM_DEFAULT_MEMORY
    // The custom checked-memory callbacks throw before any access/update.
    for(unsigned fault=0;fault<3;fault++) {
      alignas(32) std::array<uint8_t,65568> memory{};auto before=memory;
      uint32_t badEa=fault==0?16u:(fault==1?65568u:3u);
      PPCContext ctx{};uint64_t old=UINT64_C(0x1234000000000000)|uint32_t(badEa-offsets[variant/2]);
      ctx.r3.u64=old;ctx.f1.u64=UINT64_C(0x3ff0000000000000);bool caught=false;
      forceFault=fault==0;
      try{functions[variant](ctx,memory.data());}catch(const Fault&){caught=true;}
      forceFault=false;
      if(!caught||ctx.r3.u64!=old||ctx.f1.u64!=UINT64_C(0x3ff0000000000000)||memory!=before)return 7;
      ++checks;
    }
#endif
  }
#ifdef STORM_DEFAULT_MEMORY
  std::printf("LFSU/STFSU: %u native cases passed; default upstream memory macros, guest32 EA, nearest rounding\n",checks);
#else
  std::printf("LFSU/STFSU: %u native cases passed; checked-memory callbacks, guest32 EA, nearest rounding, fault ordering\n",checks);
#endif
}
'''.replace('FUNCTIONS', ','.join('memory_%x' % (0x1000+i*8) for i in range(10)))
    (work/'native.cpp').write_text(harness)
    results = {}
    for name, flags, expected in (('checked', [], 495), ('default', ['-DSTORM_DEFAULT_MEMORY'], 405)):
        run([args.clang.absolute(), '-std=c++20', '-O2', '-fsanitize=undefined',
             '-fno-sanitize-recover=all', '-I'+str(upstream/'XenonUtils'),
             '-I'+str(upstream/'thirdparty/simde'), work/'native.cpp', '-o', work/name,
             *flags, *(['-fno-sanitize-link-runtime', '-lubsan'] if args.system_ubsan else [])])
        result = run([work/name])
        if f'{expected} native cases passed' not in result:
            raise RuntimeError('Unexpected native check count')
        results[name] = result.strip()
    report={'scope':'synthetic_upstream_generated_host_guest32_addressing_only',
            'cases':900, 'checked_memory_cases':495, 'default_memory_cases':405, 'invalid_forms_rejected':3,'host':platform.machine(),
            'compiler':run([args.clang.absolute(),'--version']).splitlines()[0],
            'recompiler_sha256':hashlib.sha256(args.recompiler.read_bytes()).hexdigest(),
            'patch_sha256':hashlib.sha256((ROOT/'tools/recompilation/patches/0002-single-update.patch').read_bytes()).hexdigest(),
            'game_executed':False,'results':results}
    (work/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
