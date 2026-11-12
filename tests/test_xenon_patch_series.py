"""Synthetic metadata/source fixtures; no upstream or game files needed."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from test_xenon_pipeline import XENON


class PatchSeriesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.checkout=self.root/'upstream';self.checkout.mkdir()
        (self.root/'config').mkdir();(self.root/'patch.diff').write_text('synthetic patch content')
        (self.checkout/'source.cpp').write_text('synthetic patched source')
        self.tool=self.root/'tool';self.tool.write_text('synthetic tool identity, never executed')
        self.context=self.root/'context.h';self.context.write_text('synthetic context')
        self.config=self.root/'config/xenon_experimental_series.json'
        self.series={'id':'synthetic-guest32','base_commit':XENON.PINNED_COMMIT,'game_execution_approved':False,
                     'files':{'source.cpp':XENON.digest(self.checkout/'source.cpp')},
                     'context_sha256':XENON.digest(self.context),
                     'patches':[{'path':'patch.diff','sha256':XENON.digest(self.root/'patch.diff')}]}
        self.config.write_text(json.dumps(self.series))
        record={'path':str(self.tool),'sha256':XENON.digest(self.tool)}
        self.manifest={'source_commit':XENON.PINNED_COMMIT,'source_checkout':str(self.checkout),
                       'source_patch_series':self.series['id'],'source_patch_series_sha256':XENON.digest(self.config),
                       'analyse':record,'recomp':record,'context':{'path':str(self.context),'sha256':XENON.digest(self.context)}}

    def call(self, changes='source.cpp\n'):
        manifest=self.root/'manifest.json';manifest.write_text(json.dumps(self.manifest))
        responses=[subprocess.CompletedProcess([],0,XENON.PINNED_COMMIT),subprocess.CompletedProcess([],0,changes)]
        with patch.object(XENON,'ROOT',self.root), patch.object(XENON.subprocess,'run',side_effect=responses):
            return XENON.toolchain(manifest)

    def test_explicit_series_checks_source_and_never_approves_game_execution(self):
        result=self.call();self.assertEqual(result['source_patch_series'],self.series['id'])
        self.assertIs(result['game_execution_approved'],False)

    def test_series_config_cannot_change_after_manifest_review(self):
        self.config.write_text(self.config.read_text()+' ')
        with self.assertRaisesRegex(XENON.PipelineError,'SERIES_DIGEST'):self.call()

    def test_unknown_series_id_is_rejected(self):
        self.manifest['source_patch_series']='unreviewed-series'
        with self.assertRaisesRegex(XENON.PipelineError,'SERIES_ID_OR_POLICY'):self.call()

    def test_source_symlink_cannot_leave_checkout(self):
        source=self.checkout/'source.cpp';source.unlink();source.symlink_to(self.tool)
        with self.assertRaisesRegex(XENON.PipelineError,'PATCH_SOURCE'):self.call()

    def test_patch_bytes_cannot_change(self):
        (self.root/'patch.diff').write_text('modified patch')
        with self.assertRaisesRegex(XENON.PipelineError,'PATCH_CONTENT'):self.call()

    def test_patched_source_cannot_change(self):
        (self.checkout/'source.cpp').write_text('unreviewed source')
        with self.assertRaisesRegex(XENON.PipelineError,'PATCH_SOURCE'):self.call()

    def test_unlisted_changes_and_missing_patch_are_rejected(self):
        for names in ('source.cpp\nother.cpp\n',''):
            with self.subTest(names=names), self.assertRaisesRegex(XENON.PipelineError,'UNEXPECTED_TRACKED'):self.call(names)

    def test_context_cannot_be_replaced_even_with_new_manifest_hash(self):
        self.context.write_text('modified context');self.manifest['context']['sha256']=XENON.digest(self.context)
        with self.assertRaisesRegex(XENON.PipelineError,'PATCH_CONTEXT'):self.call()


if __name__=='__main__':unittest.main()
