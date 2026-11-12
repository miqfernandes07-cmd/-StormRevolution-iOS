import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("xenon_pipeline", ROOT / "tools/recompilation/xenon_pipeline.py")
XENON = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(XENON)


class XenonPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.private = self.root / "private"
        self.private.mkdir()
        self.xex = self.private / "default.xex"
        self.xex.write_bytes(b"synthetic adapter input; not an XEX")
        self.switches = self.private / "switches.toml"
        self.switches.write_text("# synthetic empty switch map\n")
        self.tools = {"analyse": Path("/tools/XenonAnalyse"), "recomp": Path("/tools/XenonRecomp"), "context": Path("/tools/ppc_context.h")}

    def config(self, output="generated"):
        path = self.private / "storm.toml"
        path.write_text('[main]\nfile_path="default.xex"\nswitch_table_file_path="switches.toml"\nout_directory_path=' + json.dumps(output) + '\n')
        return path

    def test_analyse_plan_exact_argv_no_execution(self):
        plan = XENON.plan_analyse(self.tools,self.xex,self.private / "new.toml",self.private)
        self.assertEqual(plan["command"],["/tools/XenonAnalyse",str(self.xex),str(self.private/"new.toml")])
        self.assertFalse((self.private/"new.toml").exists())

    def test_outside_private_rejected(self):
        with self.assertRaisesRegex(XENON.PipelineError,"PRIVATE_PATH_REQUIRED"):
            XENON.plan_analyse(self.tools,self.xex,self.root/"public.toml",self.private)
        with self.assertRaises(XENON.PipelineError):
            XENON.plan_analyse(self.tools,self.xex,self.xex,self.private)

    def test_recompile_digest_and_paths(self):
        config = self.config()
        plan = XENON.plan_recompile(self.tools,config,XENON.digest(config),self.private)
        self.assertEqual(plan["command"],["/tools/XenonRecomp",str(config),"/tools/ppc_context.h"])
        with self.assertRaisesRegex(XENON.PipelineError,"DIGEST"):
            XENON.plan_recompile(self.tools,config,"0"*64,self.private)
        config = self.config("../public")
        with self.assertRaisesRegex(XENON.PipelineError,"PRIVATE_PATH_REQUIRED"):
            XENON.plan_recompile(self.tools,config,XENON.digest(config),self.private)

    def test_symlink_output_escape_rejected(self):
        (self.private/"escape").symlink_to(self.root,target_is_directory=True)
        with self.assertRaisesRegex(XENON.PipelineError,"PRIVATE_PATH_REQUIRED"):
            XENON.plan_analyse(self.tools,self.xex,self.private/"escape/out.toml",self.private)

    def test_manifest_checks_pin_and_binary_digest(self):
        tool = self.private / "tool"
        tool.write_bytes(b"synthetic test tool identity; never executed")
        record = {"path":str(tool),"sha256":XENON.digest(tool)}
        manifest = self.private / "toolchain.json"
        manifest.write_text(json.dumps({"source_checkout":str(self.root),"source_commit":XENON.PINNED_COMMIT,
                                        "analyse":record,"recomp":record,"context":record}))
        with patch.object(XENON.subprocess,"run",side_effect=[subprocess.CompletedProcess([],0,XENON.PINNED_COMMIT),subprocess.CompletedProcess([],0)]):
            self.assertEqual(XENON.toolchain(manifest)["analyse"],tool)
        tool.write_bytes(b"changed tool")
        with patch.object(XENON.subprocess,"run",side_effect=[subprocess.CompletedProcess([],0,XENON.PINNED_COMMIT),subprocess.CompletedProcess([],0)]):
            with self.assertRaisesRegex(XENON.PipelineError,"DIGEST_MISMATCH"):
                XENON.toolchain(manifest)

    def test_invalid_manifest_and_main_schema(self):
        manifest=self.private/"toolchain.json"
        for value in ([],None,{"source_checkout":42}):
            manifest.write_text(json.dumps(value))
            with self.assertRaisesRegex(XENON.PipelineError,"SCHEMA"):
                XENON.toolchain(manifest)
        config=self.private/"invalid.toml"
        config.write_text("main=[]\n")
        with self.assertRaisesRegex(XENON.PipelineError,"TABLE_REQUIRED"):
            XENON.plan_recompile(self.tools,config,XENON.digest(config),self.private)

    def test_execution_rejects_unverified_xex_without_invoking_tool(self):
        plan=XENON.plan_analyse(self.tools,self.xex,self.private/"new.toml",self.private)
        with patch.object(XENON.subprocess,"run") as invoke:
            with self.assertRaisesRegex(XENON.PipelineError,"XEX_IDENTITY_VALIDATION_FAILED"):
                XENON.execute(plan,self.private/"run.log",self.private)
            invoke.assert_not_called()
        self.assertFalse((self.private/"run.log").exists())
        self.assertFalse((self.private/"new.toml").exists())

    def test_zero_exit_with_error_diagnostic_is_rejected(self):
        output = self.private / 'synthetic-output.toml'
        plan = {'stage': 'analyse', 'output': str(output),
                'command': [sys.executable, '-c',
                    'import pathlib,sys; pathlib.Path(sys.argv[1]).write_text("# synthetic"); print("ERROR: missing function address")', str(output)]}
        # This subprocess only tests the adapter's diagnostic contract.
        with patch.object(XENON, 'validate_identity'):
            with self.assertRaisesRegex(XENON.PipelineError, 'DIAGNOSTICS_REQUIRE_REVIEW'):
                XENON.execute(plan, self.private / 'diagnostic.log', self.private)
        self.assertTrue(output.exists())


    def test_decode_and_missing_record_diagnostics_are_rejected(self):
        for index, diagnostic in enumerate((
                'Unable to decode instruction 00000000 at 1000',
                'eqv. at 1000 has RC bit enabled but no comparison was generated')):
            with self.subTest(diagnostic=diagnostic):
                output = self.private / f'diagnostic-{index}.toml'
                plan = {'stage': 'analyse', 'output': str(output),
                        'command': [sys.executable, '-c',
                            'import pathlib,sys; pathlib.Path(sys.argv[1]).write_text("# synthetic"); print(sys.argv[2])',
                            str(output), diagnostic]}
                with patch.object(XENON, 'validate_identity'):
                    with self.assertRaisesRegex(XENON.PipelineError, 'DIAGNOSTICS_REQUIRE_REVIEW'):
                        XENON.execute(plan, self.private / f'diagnostic-{index}.log', self.private)


if __name__ == "__main__":
    unittest.main()
