"""Conservative alternate-entry CFG candidates over independently authored PE bytes."""
import importlib.util
from pathlib import Path
import struct
import unittest
from test_pe import PE, fixture, BASE

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('entry_recovery',ROOT/'tools/ppc_analysis/entry_recovery.py')
ENTRY=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(ENTRY)


def image(words):
    data=fixture('mapped')
    for index,word in enumerate(words):struct.pack_into('>I',data,0x1000+index*4,word)
    return PE.PEImage(data,'mapped')


class EntryRecoveryTests(unittest.TestCase):
    def test_straight_line_is_candidate_not_execution_proof(self):
        result=ENTRY.recover(image([0x38630001,0x4e800020]),BASE+0x1000,BASE+0x1200)
        self.assertTrue(result['candidate']);self.assertEqual(result['size'],8)
        self.assertFalse(result['game_execution_approved'])

    def test_conditional_diamond_visits_all_words(self):
        result=ENTRY.recover(image([0x4182000c,0x38600001,0x48000008,0x38600002,0x4e800020]),BASE+0x1000,BASE+0x1200)
        self.assertTrue(result['candidate']);self.assertEqual(result['visited_words'],5)

    def test_skipped_word_is_not_invented_as_code(self):
        result=ENTRY.recover(image([0x48000008,0xffffffff,0x4e800020]),BASE+0x1000,BASE+0x1200)
        self.assertFalse(result['candidate']);self.assertEqual(result['diagnostic'],'ENTRY_NONCONTIGUOUS')

    def test_conditional_lr_return_keeps_fallthrough(self):
        result=ENTRY.recover(image([0x4d820020,0x38630001,0x4e800020]),BASE+0x1000,BASE+0x1200)
        self.assertTrue(result['candidate']);self.assertEqual(result['terminal_paths'],2);self.assertEqual(result['size'],12)

    def test_skipped_nop_is_explicit_padding(self):
        result=ENTRY.recover(image([0x48000008,0x60000000,0x4e800020]),BASE+0x1000,BASE+0x1200)
        self.assertTrue(result['candidate']);self.assertEqual(result['padding_nops'],1)

    def test_indirect_flow_and_unterminated_loop_are_rejected(self):
        for words,diagnostic in (([0x4e800420],'ENTRY_INDIRECT_OR_CONDITIONAL_RETURN'),([0x48000000],'ENTRY_NO_TERMINAL'),([0],'ENTRY_INVALID_WORD')):
            with self.subTest(words=words):self.assertEqual(ENTRY.recover(image(words),BASE+0x1000,BASE+0x1200)['diagnostic'],diagnostic)

    def test_call_and_tail_target_are_metadata_only(self):
        result=ENTRY.recover(image([0x48000101,0x4e800020]),BASE+0x1000,BASE+0x1008)
        self.assertTrue(result['candidate']);self.assertEqual(result['outgoing_targets'],[BASE+0x1100])
        result=ENTRY.recover(image([0x48000100]),BASE+0x1000,BASE+0x1004)
        self.assertTrue(result['candidate']);self.assertEqual(result['size'],4)

    def test_bounds_machine_and_modes_are_checked(self):
        pe=image([0x4e800020])
        for entry,end,max_words in ((BASE+0x1001,BASE+0x1200,4),(BASE+0x1000,BASE+0x4000,4),(BASE+0x1000,BASE+0x1200,0),('bad',BASE+0x1200,4)):
            with self.subTest(entry=entry),self.assertRaises(ENTRY.RecoveryError):ENTRY.recover(pe,entry,end,max_words)
        pe.machine=0x14c
        with self.assertRaisesRegex(ENTRY.RecoveryError,'MACHINE'):ENTRY.recover(pe,BASE+0x1000,BASE+0x1200)

    def test_pdata_is_big_endian_range_metadata(self):
        data=fixture('mapped');struct.pack_into('<H',data,0x86,3)
        off=0x1c8;data[off:off+8]=b'.pdata\0\0'
        for delta,value in ((8,16),(12,0x2800),(16,16),(20,0x2800),(36,0x40000040)):struct.pack_into('<I',data,off+delta,value)
        struct.pack_into('>4I',data,0x2800,BASE+0x1000,(2<<8)|0x40000000,BASE+0x1010,2<<8)
        pe=PE.PEImage(data,'mapped');self.assertEqual(ENTRY.pdata_ranges(pe),[(BASE+0x1000,BASE+0x1008),(BASE+0x1010,BASE+0x1018)])
        struct.pack_into('>I',data,0x2804,0)
        with self.assertRaisesRegex(ENTRY.RecoveryError,'PDATA_RANGE'):ENTRY.pdata_ranges(PE.PEImage(data,'mapped'))

    def test_audit_schema_and_repeated_targets(self):
        pe=image([0x4e800020]);site={'token':'XENON_UNRESOLVED_STATIC_CALL','target':BASE+0x1000}
        report=ENTRY.analyse(pe,{'blocked_sites':[site,site]});self.assertEqual(report['unique_targets'],1);self.assertEqual(report['candidates'][0]['omitted_calls'],2)
        self.assertEqual(ENTRY.analyse(pe,{'blocked_sites':[{}]})['unique_targets'],0)
        for invalid in ({},{'blocked_sites':[{'token':site['token'],'target':True}]}):
            with self.assertRaises(ENTRY.RecoveryError):ENTRY.analyse(pe,invalid)


if __name__=='__main__':unittest.main()
