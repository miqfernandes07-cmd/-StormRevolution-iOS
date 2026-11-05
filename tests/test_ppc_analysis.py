"""Synthetic instruction bytes only; no commercial program is analyzed here."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('inventory', ROOT / 'tools/ppc_analysis/inventory.py')
PPC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PPC)
BLR, BCTR, BCTRL = 0x4E800020, 0x4E800420, 0x4E800421


def words(*values):
    return b''.join(struct.pack('>I', value) for value in values)


def branch(displacement, aa=0, lk=0):
    return (18 << 26) | (displacement & 0x03FFFFFC) | (aa << 1) | lk


def conditional(displacement, bo=12, bi=2, aa=0, lk=0):
    return (16 << 26) | (bo << 21) | (bi << 16) | (displacement & 0xFFFC) | (aa << 1) | lk


class InventoryTests(unittest.TestCase):
    def test_known_integer_taxonomy_and_aot_contract(self):
        add = (31 << 26) | (3 << 21) | (4 << 16) | (5 << 11) | (266 << 1)
        bit_or = (31 << 26) | (3 << 21) | (4 << 16) | (5 << 11) | (444 << 1)
        data = words(0x38600001, 0x3C80FFFF, 0x6063ABCD, add, bit_or, BLR)
        report = PPC.inventory(data, 0x82000000)
        self.assertEqual(report['instruction_histogram'], {'add':1,'addi':1,'addis':1,'blr':1,'or':1,'ori':1})
        self.assertEqual(report['known_word_count'], 6)
        self.assertTrue(report['synthetic_aot_check']['accepted'])
        self.assertFalse(report['synthetic_aot_check']['compiled'])
        self.assertFalse(report['synthetic_aot_check']['executed'])

    def test_calls_produce_candidates_not_function_boundaries(self):
        report = PPC.inventory(words(branch(8, lk=1), BLR, BLR), 0x82000000)
        self.assertEqual(report['function_candidates'], [
            {'address':'0x82000000','reasons':['selected_entry'],'in_region':True,'boundary_verified':False},
            {'address':'0x82000008','reasons':['direct_link_target'],'in_region':True,'boundary_verified':False}])
        self.assertEqual(report['control_flow_edges'][0]['kind'], 'possible_call')
        self.assertEqual(report['control_flow_edges'][1]['target'], '0x82000004')
        self.assertEqual(report['analysis_status']['function_boundaries'], 'not_implemented')
        self.assertFalse(report['synthetic_aot_check']['accepted'])

    def test_call_to_entry_merges_candidate_reasons(self):
        report = PPC.inventory(words(branch(0, lk=1)), 0)
        self.assertEqual(len(report['function_candidates']), 1)
        self.assertEqual(report['function_candidates'][0]['reasons'], ['direct_link_target','selected_entry'])

    def test_backward_relative_branch(self):
        report = PPC.inventory(words(0x60000000, branch(-4)), 0x82000000)
        reference = report['branch_references'][0]
        self.assertEqual(reference['source'], '0x82000004')
        self.assertEqual(reference['target'], '0x82000000')
        self.assertEqual(reference['displacement'], -4)
        self.assertFalse(reference['relative_address_wrapped'])
        self.assertEqual(report['synthetic_aot_check']['first_diagnostic']['code'], 'AOT_UNSUPPORTED_BRANCH')

    def test_minimum_branch_displacements(self):
        report = PPC.inventory(words(branch(-(1 << 25)), conditional(-(1 << 15))), 0x82000000)
        self.assertEqual(report['branch_references'][0]['target'], '0x80000000')
        self.assertEqual(report['branch_references'][1]['target'], '0x81FF8004')

    def test_branch_address_wrap_and_absolute_negative(self):
        for base, instruction, target, wrapped in [
            (0, branch(-4), '0xFFFFFFFC', True),
            (0xFFFFFFFC, branch(4), '0x00000000', True),
            (0x82000000, branch(-4, aa=1), '0xFFFFFFFC', False),
            (0, conditional(-4), '0xFFFFFFFC', True),
            (0xFFFFFFFC, conditional(4), '0x00000000', True),
            (0x82000000, conditional(-4, aa=1), '0xFFFFFFFC', False)]:
            with self.subTest(base=base, instruction=instruction):
                reference = PPC.inventory(words(instruction), base)['branch_references'][0]
                self.assertEqual(reference['target'], target)
                self.assertEqual(reference['relative_address_wrapped'], wrapped)

    def test_conditional_aa_lk_and_conservative_edges(self):
        for aa in (0,1):
            for lk in (0,1):
                with self.subTest(aa=aa,lk=lk):
                    report = PPC.inventory(words(conditional(8, bo=20, bi=31, aa=aa, lk=lk), BLR, BLR), 0x1000)
                    ref = report['branch_references'][0]
                    self.assertEqual(ref['target'], '0x00000008' if aa else '0x00001008')
                    self.assertEqual((ref['bo'],ref['bi'],ref['absolute'],ref['link']), (20,31,bool(aa),bool(lk)))
                    self.assertEqual(ref['condition_evaluation'], 'not_implemented')
                    self.assertEqual(len(report['control_flow_edges']), 2)
                    self.assertEqual(len(report['function_candidates']), 2 if lk else 1)

    def test_plain_branch_is_not_a_function_candidate(self):
        report = PPC.inventory(words(branch(8), BLR, BLR), 0)
        self.assertEqual(len(report['function_candidates']), 1)
        self.assertEqual(len(report['control_flow_edges']), 1)
        self.assertTrue(report['synthetic_aot_check']['accepted'])

    def test_indirect_targets_and_jump_tables_remain_unresolved(self):
        report = PPC.inventory(words(BLR,BCTR,BCTRL), 0x1000)
        self.assertEqual([row['target_register'] for row in report['indirect_branches']], ['lr','ctr','ctr'])
        self.assertEqual(report['analysis_status']['jump_table_recovery'], 'not_implemented')
        self.assertEqual(report['branch_references'], [])
        self.assertEqual(report['control_flow_edges'][0]['target'], '0x0000100C')
        self.assertFalse(report['control_flow_edges'][0]['target_in_region'])

    def test_unknown_and_flag_variants_report_exact_addresses(self):
        add = (31 << 26) | (266 << 1)
        report = PPC.inventory(words(0, add | 1, add | 0x400, BLR | 1), 0x1000)
        self.assertEqual(report['unknown_word_count'], 4)
        self.assertEqual([d['address'] for d in report['diagnostics']], ['0x00001000','0x00001004','0x00001008','0x0000100C'])
        self.assertEqual(report['diagnostics'][1]['code'], 'PPC_INVENTORY_UNSUPPORTED_VARIANT')
        self.assertEqual(report['diagnostics'][3]['code'], 'PPC_INVENTORY_UNSUPPORTED_INDIRECT_VARIANT')
        self.assertEqual(report['control_flow_edges'], [])

    def test_scans_unreachable_words_without_claiming_reachability(self):
        report = PPC.inventory(words(branch(8), 0, BLR), 0)
        self.assertEqual(report['unknown_word_count'], 1)
        self.assertEqual(report['diagnostics'][0]['address'], '0x00000004')
        self.assertEqual(report['analysis_status']['reachability'], 'not_implemented')

    def test_external_call_is_explicit_candidate_outside_region(self):
        report = PPC.inventory(words(branch(0x100,lk=1)), 0x1000)
        self.assertFalse(report['function_candidates'][1]['in_region'])
        self.assertFalse(report['branch_references'][0]['target_in_region'])

    def test_input_bounds_and_container_rejection(self):
        cases = [(b'',0,None),(b'\0',0,None),(words(BLR),1,None),(words(BLR),-4,None),
                 (words(BLR,BLR),0xFFFFFFFC,None),(words(BLR),0,4),
                 (words(BLR),0,1),(b'XEX2',0,None),(b'XEX1',0,None),
                 (b'\0'*(PPC.MAX_REGION_SIZE+4),0,None)]
        for data,base,entry in cases:
            with self.subTest(length=len(data),base=base,entry=entry), self.assertRaises(PPC.InventoryError):
                PPC.inventory(data,base,entry)

    def test_nondefault_entry_and_determinism(self):
        data = words(0x60000000,BLR)
        report = PPC.inventory(data,0x1000,0x1004)
        self.assertEqual(report['entry_address'], '0x00001004')
        self.assertEqual(report, PPC.inventory(data,0x1000,0x1004))

    def test_cli_refuses_hardlink_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory)/'raw.ppc', Path(directory)/'alias.json'
            source.write_bytes(words(BLR))
            os.link(source, output)
            command=[sys.executable,str(ROOT/'tools/ppc_analysis/inventory.py'),'--raw-ppc',str(source),'--base','0','--output',str(output)]
            result = subprocess.run(command,capture_output=True)
            self.assertEqual(result.returncode,1)
            self.assertIn(b'PPC_INVENTORY_OUTPUT',result.stderr)
            self.assertEqual(source.read_bytes(),words(BLR))

    def test_cli_known_unknown_malformed_and_no_input_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory)/'raw.ppc', Path(directory)/'report.json'
            source.write_bytes(words(BLR))
            command=[sys.executable,str(ROOT/'tools/ppc_analysis/inventory.py'),'--raw-ppc',str(source),'--base','0','--output',str(output)]
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
            self.assertEqual(json.loads(output.read_text())['word_count'],1)
            source.write_bytes(words(0))
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,2)
            self.assertEqual(json.loads(output.read_text())['unknown_word_count'],1)
            source.write_bytes(b'XEX2')
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,1)
            source.write_bytes(words(BLR))
            self.assertEqual(subprocess.run(command[:-1]+[str(source)],capture_output=True).returncode,1)
            self.assertEqual(source.read_bytes(),words(BLR))


if __name__ == '__main__':
    unittest.main()
