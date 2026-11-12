"""Emitted-code contract tests using own tiny C++ snippets, never game code."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_xenon_pipeline import XENON


class GeneratedAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.output=self.root/'generated';self.output.mkdir()

    def test_detects_trap_unreachable_and_counts_indirect_sites(self):
        (self.output/'sample.cpp').write_text('void f(){\n__builtin_debugtrap();\n__builtin_trap ();\n__builtin_unreachable();\nPPC_CALL_INDIRECT_FUNC(7);\n}\n')
        result=XENON.audit_generated(self.output)
        self.assertEqual([x['line'] for x in result['blocked_sites']],[2,3,4])
        self.assertEqual(result['indirect_call_sites'],1)
        self.assertFalse(result['game_execution_approved'])

    def test_ignores_literals_and_comments_preserving_line_numbers(self):
        (self.output/'sample.cpp').write_text('/* __builtin_trap();\n__builtin_unreachable(); */\nconst char* s="__builtin_debugtrap()";\n// __builtin_trap();\nvoid f(){__builtin_trap();}\n')
        result=XENON.audit_generated(self.output)
        self.assertEqual(result['blocked_sites'],[{'file':'sample.cpp','line':5,'token':'__builtin_trap'}])

    def test_omitted_direct_call_marker_is_rejected(self):
        (self.output/'sample.cpp').write_text('const char* s="// ERROR 1234";\n\n// ERROR 1234\n')
        result=XENON.audit_generated(self.output)
        self.assertEqual(result['blocked_sites'],[{'file':'sample.cpp','line':3,'token':'XENON_UNRESOLVED_STATIC_CALL','target':0x1234}])

    def test_undecoded_zero_is_not_a_nop(self):
        (self.output/'sample.cpp').write_text('void f(){\n// .long 0x0\n}\n')
        self.assertEqual(XENON.audit_generated(self.output)['blocked_sites'],[{'file':'sample.cpp','line':2,'token':'XENON_UNDECODED_WORD'}])

    def test_unexpected_modes_in_log_are_rejected(self):
        for index,diagnostic in enumerate(('Unexpected D3D color pack instruction at 1000','Function 1000 ends prematurely')):
            output=self.root/('mode-'+str(index));log=self.root/('mode-'+str(index)+'.log')
            command=[sys.executable,'-c','print('+repr(diagnostic)+')']
            with patch.object(XENON,'validate_identity'),self.assertRaisesRegex(XENON.PipelineError,'DIAGNOSTICS_REQUIRE_REVIEW'):
                XENON.execute({'stage':'recompile','output':str(output),'command':command},log,self.root)

    def test_source_symlink_cannot_escape_output(self):
        outside=self.root/'outside.cpp';outside.write_text('void f(){}')
        (self.output/'alias.cpp').symlink_to(outside)
        with self.assertRaisesRegex(XENON.PipelineError,'SOURCE_ESCAPE'):XENON.audit_generated(self.output)

    def test_header_safety_helpers_are_outside_cpp_gate(self):
        (self.output/'context.h').write_text('void guard(){__builtin_debugtrap();}')
        (self.output/'sample.cpp').write_text('void f(){}')
        self.assertEqual(XENON.audit_generated(self.output)['blocked_sites'],[])

    def test_suppressing_trap_macro_is_still_flagged(self):
        (self.output/'sample.cpp').write_text('#define __builtin_debugtrap()\n')
        self.assertEqual(len(XENON.audit_generated(self.output)['blocked_sites']),1)

    def test_zero_exit_and_clean_log_do_not_accept_trapped_generated_code(self):
        output=self.root/'new-generated';log=self.root/'run.log'
        command=[sys.executable,'-c','import pathlib,sys; (pathlib.Path(sys.argv[1])/"sample.cpp").write_text("void f(){__builtin_debugtrap();}")',str(output)]
        plan={'stage':'recompile','output':str(output),'command':command}
        with patch.object(XENON,'validate_identity'):
            with self.assertRaisesRegex(XENON.PipelineError,'GENERATED_CODE_REQUIRES_REVIEW'):
                XENON.execute(plan,log,self.root)
        report=json.loads((self.root/'run.log.audit.json').read_text())
        self.assertEqual(len(report['blocked_sites']),1)
        self.assertFalse(report['game_execution_approved'])


if __name__=='__main__':unittest.main()
