"""Own emitter-shaped snippets; no commercial inputs or native title execution."""
import hashlib
import importlib.util
import json
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
