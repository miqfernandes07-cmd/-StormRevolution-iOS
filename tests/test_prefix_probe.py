"""Own emitter-shaped snippets; no commercial inputs or native title execution."""
import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('prefix_probe',ROOT/'tools/recompilation/prefix_probe.py')
PROBE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(PROBE)


def function(name='own',body='return;'):
    return 'PPC_FUNC_IMPL(__imp__'+name+') {\n\t'+body+'\n}\n'


class PrefixTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve();self.generated=self.root/'generated';self.generated.mkdir()

    def test_selected_function_body_is_preserved(self):
        source=function(body='if (ctx.r3.u64) { ctx.r4.u64=1; }\n\treturn;')
        (self.generated/'own.cpp').write_text(source+function('other'))
        self.assertEqual(PROBE.extract(self.generated,['own']),{'own':source.rstrip()})

    def test_invalid_names_and_duplicates_are_rejected(self):
        for names in ([],['own','own'],['bad-name'],['x");'],[1],'own',['x']*33):
            with self.subTest(names=names),self.assertRaisesRegex(PROBE.ProbeError,'FUNCTION_LIST'):PROBE.extract(self.generated,names)

    def test_missing_and_duplicate_definition_are_rejected(self):
        with self.assertRaisesRegex(PROBE.ProbeError,'FUNCTION_MISSING'):PROBE.extract(self.generated,['own'])
        (self.generated/'a.cpp').write_text(function());(self.generated/'b.cpp').write_text(function())
        with self.assertRaisesRegex(PROBE.ProbeError,'DUPLICATE_FUNCTION'):PROBE.extract(self.generated,['own'])

    def test_incomplete_and_raw_memory_paths_are_rejected(self):
        for body in ('__builtin_debugtrap();','__builtin_unreachable();','// ERROR 1234','// .long 0x0','auto p=base + 4;','simde_mm_load_si128(p);','__sync_bool_compare_and_swap(p,0,1);','__atomic_load_n(p,0);'):
            (self.generated/'a.cpp').write_text(function(body=body))
            with self.subTest(body=body),self.assertRaisesRegex(PROBE.ProbeError,'UNQUALIFIED_SELECTED_FUNCTION'):PROBE.extract(self.generated,['own'])

    def test_unselected_incomplete_function_does_not_approve_whole_image(self):
        (self.generated/'a.cpp').write_text(function()+function('other','__builtin_trap();'))
        self.assertEqual(list(PROBE.extract(self.generated,['own'])),['own'])

    def test_symlink_and_size_limits(self):
        outside=self.root/'outside.cpp';outside.write_text(function());(self.generated/'alias.cpp').symlink_to(outside)
        with self.assertRaisesRegex(PROBE.ProbeError,'SOURCE_ESCAPE'):PROBE.extract(self.generated,['own'])
        with self.assertRaisesRegex(PROBE.ProbeError,'SIZE_LIMIT'):PROBE.bounded(outside,3)

    def test_context_preamble_is_exact_and_layout_cannot_drift(self):
        original=b'struct PPCContext { int value; };\n'
        preamble=b'#pragma once\n#include "ppc_config.h"\n\n'
        PROBE.verify_context(preamble+original,original)
        for changed in (original,preamble+original+b'int extra;\n',b'// alternate\n'+original):
            with self.assertRaisesRegex(PROBE.ProbeError,'ABI_MISMATCH'):PROBE.verify_context(changed,original)

    def test_kernel_wrappers_execute_with_explicit_guest_process_state(self):
        # Compile the actual probe imports against an own emitter-shaped context.
        # This verifies the new ABI adapters, not commercial instructions or boot.
        context = '#pragma once\n#include <cstdint>\nunion Reg{std::uint64_t u64;std::uint32_t u32;};\nstruct PPCContext{Reg r1,r2,r3,r4,r5,r6,r7;};\n#define PPC_FUNC(n) void n(PPCContext& ctx, std::uint8_t* base)\n'
        (self.root/'ppc_recomp_shared.h').write_text(context)
        handlers=(ROOT/'tools/recompilation/prefix_probe_main.cpp.in').read_text().split('@GUARDS@')[0]
        main = r"""
int main(){
    PPCContext ctx{};uint8_t base[32]{};bool failed=false;
    try{__imp__KeGetCurrentProcessType(ctx,base);}catch(const std::runtime_error&){failed=true;}
    if(!failed)return 1;
    storm::memory::AddressSpace space;storm::kernel::ProcessState state(space,0x80010000);
    process_state=&state;kernel_space=&space;
    __imp__KeGetCurrentProcessType(ctx,base);if(ctx.r3.u64!=1)return 2;
    ctx.r3.u64=2;__imp__KeSetCurrentProcessType(ctx,base);
    if(ctx.r3.u64!=2||space.load(0x8001002f,1)!=2)return 3;
    space.store(0x8001002f,1,0);__imp__KeGetCurrentProcessType(ctx,base);
    if(ctx.r3.u64!=0)return 4;
    space.map(0x20000,28,storm::memory::Access::read_write);
    ctx.r3.u64=0x20000;__imp__RtlInitializeCriticalSection(ctx,base);
    if(ctx.r3.u64!=0x20000||space.load(0x20010,4)!=0xffffffff)return 5;
    ctx.r4.u64=257;__imp__RtlInitializeCriticalSectionAndSpinCount(ctx,base);
    if(ctx.r3.u64!=0||space.load(0x20001,1)!=2)return 6;
    return 0;
}
"""
        source=self.root/'kernel_probe.cpp';source.write_text(handlers+main)
        executable=self.root/'kernel_probe'
        compiler=shlex.split(os.environ.get('CXX','c++'))
        sources=['memory/address_space.cpp','kernel/executable_module.cpp','kernel/virtual_memory.cpp','kernel/process_state.cpp']
        result=subprocess.run(compiler+['-std=c++17','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(ROOT/'runtime'),'-I'+str(self.root),str(source)]+[str(ROOT/'runtime'/x) for x in sources]+['-o',str(executable)],capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)
        result=subprocess.run([str(executable)],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(result.stderr,'')

    def test_private_config_hash_and_schema(self):
        with patch.object(PROBE,'ROOT',self.root):
            private=self.root/'private';private.mkdir();path=private/'probe.json'
            data=json.dumps({'function_sha256':{},'header_sha256':{},'module_layout':{}}).encode();path.write_bytes(data)
            self.assertEqual(PROBE.checked_config(path,hashlib.sha256(data).hexdigest())['module_layout'],{})
            with self.assertRaisesRegex(PROBE.ProbeError,'CONFIG_DIGEST'):PROBE.checked_config(path,'0'*64)
            with self.assertRaisesRegex(PROBE.ProbeError,'PRIVATE_PATH'):PROBE.private(self.root/'public')
            path.write_text('[]')
            with self.assertRaisesRegex(PROBE.ProbeError,'OBJECT_REQUIRED'):PROBE.checked_config(path,PROBE.sha(path.read_bytes()))
            path.write_text('{}')
            with self.assertRaisesRegex(PROBE.ProbeError,'TABLES_REQUIRED'):PROBE.checked_config(path,PROBE.sha(path.read_bytes()))


if __name__=='__main__':unittest.main()
