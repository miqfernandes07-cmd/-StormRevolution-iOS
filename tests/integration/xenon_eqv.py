#!/usr/bin/env python3
"""Explicit integration test of a patched upstream tool; no game input required.

Not included in default discovery: requires separately audited XenonRecomp,
SIMDe headers and Clang >=18. Outputs go to a new directory under build/.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def elf_fixture(record=False):
    # Independent PPC X-form encodings: RS, RA(destination), RB, XO=284.
    code = b''.join(struct.pack('>II', (31 << 26) | (rs << 21) | (ra << 16) |
                               (rb << 11) | (284 << 1) | int(record), 0x4e800020)
                    for rs, ra, rb in ((4, 3, 5), (3, 3, 5), (4, 5, 5)))
    names = b'\0.text\0.shstrtab\0'
    table = (52 + len(code) + len(names) + 3) & ~3
    ident = b'\x7fELF\x01\x02\x01' + bytes(9)
    header = struct.pack('>16sHHIIIIIHHHHHH', ident, 1, 20, 1, 0x1000,
                         0, table, 0, 52, 0, 0, 40, 3, 2)
    body = (header + code + names).ljust(table, b'\0')
    text = struct.pack('>10I', 1, 1, 6, 0x1000, 52, len(code), 0, 0, 4, 0)
    strings = struct.pack('>10I', 7, 3, 0, 0x2000, 52 + len(code), len(names), 0, 0, 1, 0)
    return body + bytes(40) + text + strings


def run(args):
    result = subprocess.run([str(x) for x in args], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {result.stdout}\n{result.stderr}')
    return result.stdout + result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--recompiler', type=Path, required=True)
    parser.add_argument('--clang', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--system-ubsan', action='store_true',
                        help='Linux toolchains without compiler-rt: link system libubsan')
    args = parser.parse_args()
    work = args.work.resolve()
    if not work.is_relative_to(ROOT / 'build') or work.exists():
        parser.error('--work must be a new directory under build/')
    upstream = args.upstream.resolve()
    work.mkdir(parents=True)
    for name, record in (('plain', False), ('record', True)):
        source, dest = work / name / 'input', work / name / 'output'
        source.mkdir(parents=True)
        dest.mkdir()
        (source / 'eqv.o').write_bytes(elf_fixture(record))
        log = run([args.recompiler.resolve(), source, dest])
        (work / name / 'generation.log').write_text(log)
        generated = (dest / 'eqv.cpp').read_text()
        if record:
            if log.count('Unrecognized instruction') != 3 or 'unimplemented instructions' not in log:
                raise RuntimeError('EQV. must stay explicitly rejected by this nonrecord patch')
        elif 'Unrecognized instruction' in log or 'unimplemented' in log or generated.count('.u64 = ~(') != 3:
            raise RuntimeError('EQV generation is incomplete')
    harness = r'''
#include "plain/output/eqv.cpp"
#include <cstdio>
#include <cstdlib>
#include <array>
uint64_t reference(uint64_t a, uint64_t b) {
  uint64_t value=0;
  for(unsigned bit=0;bit<64;bit++)
    if (((a>>bit)&1)==((b>>bit)&1)) value |= UINT64_C(1)<<bit;
  return value;
}
int main() {
  const std::array<uint64_t,8> edge{0,UINT64_MAX,1,UINT64_C(0x8000000000000000),
    UINT64_C(0x7fffffff),UINT64_C(0x80000000),UINT64_C(0xaaaaaaaaaaaaaaaa),UINT64_C(0x5555555555555555)};
  uint64_t seed=42; unsigned checks=0;
  for(unsigned i=0;i<1088;i++) {
    auto next=[&](){seed=seed*UINT64_C(6364136223846793005)+1;return seed;};
    uint64_t a=i<64?edge[i/8]:next(), b=i<64?edge[i%8]:next();
    for(unsigned variant=0;variant<3;variant++) {
      PPCContext ctx{}; alignas(32) uint8_t memory[32]{};
      ctx.r3.u64=variant==1?a:17;ctx.r4.u64=a;ctx.r5.u64=b;
      ctx.xer.ca=1;ctx.xer.so=1;ctx.cr0.lt=1;ctx.cr0.gt=0;ctx.cr0.eq=1;ctx.cr0.so=0;
      if(variant==0) eqv_1000(ctx,memory);
      if(variant==1) eqv_1008(ctx,memory);
      if(variant==2) eqv_1010(ctx,memory);
      uint64_t actual=variant==2?ctx.r5.u64:ctx.r3.u64;
      if(actual!=reference(a,b)||ctx.r4.u64!=a||ctx.xer.ca!=1||ctx.xer.so!=1||
         ctx.cr0.lt!=1||ctx.cr0.gt!=0||ctx.cr0.eq!=1||ctx.cr0.so!=0||
         (variant!=2&&ctx.r5.u64!=b)||(variant==2&&ctx.r3.u64!=17)) return 1;
      ++checks;
    }
  }
  std::printf("EQV upstream-generated native functions: %u vectors passed; EQV. remains unsupported\n",checks);
}
'''
    (work / 'native.cpp').write_text(harness)
    run([args.clang.resolve(), '-std=c++20', '-O2', '-fsanitize=undefined',
         '-fno-sanitize-recover=all', '-I' + str(upstream / 'XenonUtils'),
         '-I' + str(upstream / 'thirdparty/simde'), work / 'native.cpp', '-o', work / 'native',
         *(['-fno-sanitize-link-runtime', '-lubsan'] if args.system_ubsan else [])])
    output = run([work / 'native'])
    report = {'scope': 'synthetic_eqv_upstream_generated_native_host_only',
              'vectors': 3264, 'eqv_record_rejected': True, 'game_executed': False,
              'host': platform.machine(), 'system': platform.system(),
              'compiler': run([args.clang.resolve(), '--version']).splitlines()[0],
              'upstream_commit': run(['git', '-C', upstream, 'rev-parse', 'HEAD']).strip(),
              'patch_sha256': hashlib.sha256((ROOT / 'tools/recompilation/patches/0001-eqv-nonrecord.patch').read_bytes()).hexdigest(),
              'context_sha256': hashlib.sha256((upstream / 'XenonUtils/ppc_context.h').read_bytes()).hexdigest(),
              'recompiler_sha256': hashlib.sha256(args.recompiler.read_bytes()).hexdigest(),
              'result': output.strip()}
    (work / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
