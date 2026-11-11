"""PE32 files and mapped images authored entirely as synthetic test fixtures."""
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
SPEC = importlib.util.spec_from_file_location('storm_pe', ROOT / 'tools/xex_analysis/pe.py')
PE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PE)
BASE = 0x82000000


def fixture(layout='file'):
    data = bytearray(0x600 if layout == 'file' else 0x3000)
    def u16(offset, value): struct.pack_into('<H', data, offset, value)
    def u32(offset, value): struct.pack_into('<I', data, offset, value)
    data[:2] = b'MZ'
    u32(0x3c, 0x80)
    data[0x80:0x84] = b'PE\0\0'
    u16(0x84, 0x1f2)
    u16(0x86, 2)
    u16(0x94, 224)
    u16(0x98, 0x10b)
    u32(0xa8, 0x1000)
    u32(0xb4, BASE)
    u32(0xb8, 0x1000)
    u32(0xbc, 0x200)
    u32(0xd0, 0x3000)
    u32(0xd4, 0x200)
    u32(0xf4, 16)
    for off, name, vs, rva, raw, flags in ((0x178,b'.text',0x180,0x1000,0x200,0x60000020),
                                         (0x1a0,b'.data',0x300,0x2000,0x400,0xc0000040)):
        data[off:off+len(name)] = name
        u32(off+8, vs)
        u32(off+12, rva)
        u32(off+16, 0x200)
        u32(off+20, raw)
        u32(off+36, flags)
    text = 0x200 if layout == 'file' else 0x1000
    data[text:text+8] = bytes.fromhex('0000012301000123')
    return data


def xex_report(addresses=None):
    return {'security': {'load_address': BASE},
            'imports': [{'name': 'synthetic.xex', 'record_addresses': addresses if addresses is not None else [BASE+0x1000,BASE+0x1004]}]}


class PETests(unittest.TestCase):
    def test_file_headers_and_executable_section(self):
        report = PE.PEImage(fixture(), 'file').report()
        self.assertEqual(report['machine'], '0x01f2')
        self.assertEqual(report['entry_address'], BASE+0x1000)
        self.assertEqual(report['entry_sections'], ['.text'])
        self.assertTrue(report['sections'][0]['executable'])
        self.assertFalse(report['sections'][1]['executable'])
        self.assertEqual(report['analysis_status']['functions'], 'not_implemented')

    def test_file_and_mapped_rva_equivalence(self):
        file = PE.PEImage(fixture(), 'file')
        mapped = PE.PEImage(fixture('mapped'), 'mapped')
        self.assertEqual(file.rva_bytes(0x1000,8), mapped.rva_bytes(0x1000,8))
        self.assertEqual(file.rva_bytes(0,2), b'MZ')
        self.assertEqual(mapped.rva_bytes(0x2200,4), bytes(4))
        with self.assertRaisesRegex(PE.PEError,'PE_RVA_UNBACKED'):
            file.rva_bytes(0x2200,4)

    def test_layout_must_be_explicit_and_consistent(self):
        with self.assertRaisesRegex(PE.PEError,'PE_LAYOUT'):
            PE.PEImage(fixture(),'auto')
        with self.assertRaisesRegex(PE.PEError,'PE_MAPPED_TRUNCATED'):
            PE.PEImage(fixture(),'mapped')

    def test_all_file_truncations_rejected(self):
        data = fixture()
        for length in range(len(data)):
            with self.subTest(length=length), self.assertRaises(PE.PEError):
                PE.PEImage(data[:length], 'file')

    def test_mapped_unused_tail_can_be_absent_but_is_not_fabricated(self):
        data=fixture('mapped')[:0x2300]
        image=PE.PEImage(data,'mapped')
        self.assertEqual(image.report()['available_size'],0x2300)
        self.assertEqual(image.report()['diagnostics'][0]['code'],'PE_IMAGE_TAIL_UNAVAILABLE')
        with self.assertRaisesRegex(PE.PEError,'PE_BOUNDS'): image.rva_bytes(0x2900,4)
        with self.assertRaisesRegex(PE.PEError,'PE_MAPPED_TRUNCATED'): PE.PEImage(data[:-1],'mapped')

    def test_dos_nt_and_optional_magic(self):
        for off, replacement in ((0,b'NO'),(0x80,b'BAD!'),(0x98,b'\x0b\x02')):
            data=fixture();data[off:off+len(replacement)]=replacement
            with self.subTest(offset=off), self.assertRaises(PE.PEError):
                PE.PEImage(data,'file')

    def test_malformed_ranges_and_counts(self):
        for off, value, code in ((0x3c,0xffffff00,'PE_BOUNDS'),(0xd0,0,'PE_IMAGE_RANGE'),
                                  (0xd0,0xffffffff,'PE_IMAGE_RANGE'),(0xd4,0x180,'PE_HEADERS_SIZE'),
                                  (0xa8,0x3000,'PE_ENTRY_RANGE'),(0xf4,17,'PE_DIRECTORY_COUNT'),
                                  (0x178+12,0xfffffffc,'PE_SECTION_RANGE'),
                                  (0x178+20,0x100,'PE_RAW_RANGE')):
            data=fixture();struct.pack_into('<I',data,off,value)
            with self.subTest(offset=off), self.assertRaisesRegex(PE.PEError,code):
                PE.PEImage(data,'file')
        for count in (0,97):
            data=fixture();struct.pack_into('<H',data,0x86,count)
            with self.assertRaisesRegex(PE.PEError,'PE_SECTION_COUNT'): PE.PEImage(data,'file')

    def test_overlapping_sections(self):
        for off in (0x1a0+12,0x1a0+20):
            data=fixture();struct.pack_into('<I',data,off,0x1000 if off==0x1a0+12 else 0x200)
            with self.assertRaisesRegex(PE.PEError,'PE_SECTION_OVERLAP'): PE.PEImage(data,'file')

    def test_rva_invalid_and_cross_section(self):
        image=PE.PEImage(fixture(),'file')
        for rva,size in ((-1,4),(0x3000,1),(0x1000,-1),(0x1800,4),(0x11ff,2)):
            with self.subTest(rva=rva,size=size),self.assertRaises(PE.PEError): image.rva_bytes(rva,size)

    def test_import_descriptor_endianness_and_pairing(self):
        for layout in ('file','mapped'):
            report=PE.resolve_xex_imports(PE.PEImage(fixture(layout),layout),xex_report())
            records=report['libraries'][0]['records']
            self.assertEqual([r['ordinal'] for r in records],[0x123,0x123])
            self.assertEqual(records[0]['kind'],'value_slot')
            self.assertEqual(records[1]['kind'],'thunk')
            self.assertEqual(records[1]['paired_value_address'],BASE+0x1000)
            self.assertEqual(records[0]['thunk_address'],BASE+0x1004)
            self.assertEqual(report['diagnostics'],[])

    def test_unknown_and_unpaired_imports_are_diagnosed(self):
        data=fixture();data[0x200:0x204]=bytes.fromhex('99000123')
        report=PE.resolve_xex_imports(PE.PEImage(data,'file'),xex_report())
        self.assertEqual([d['code'] for d in report['diagnostics']],['XEX_IMPORT_UNKNOWN_TYPE','XEX_IMPORT_THUNK_UNPAIRED'])

    def test_import_schema_and_addresses(self):
        image=PE.PEImage(fixture(),'file')
        for report in (None,[],{}, {'imports':[],'security':{'load_address':0}},
                       xex_report([BASE+1]),xex_report([BASE-4]),xex_report([BASE+0x4000])):
            with self.subTest(report=report),self.assertRaises(PE.PEError): PE.resolve_xex_imports(image,report)

    def test_cli_reports_and_preserves_source_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'image.bin';source.write_bytes(fixture())
            output=Path(directory)/'report.json'
            command=[sys.executable,str(ROOT/'tools/xex_analysis/pe.py'),str(source),'--layout','file','--output',str(output)]
            run=subprocess.run(command,capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(json.loads(output.read_text())['format'],'PE32')
            output.unlink();os.link(source,output)
            run=subprocess.run(command,capture_output=True)
            self.assertEqual(run.returncode,1)
            self.assertIn(b'PE_OUTPUT_COLLISION',run.stderr)
            self.assertEqual(source.read_bytes(),fixture())


if __name__=='__main__':
    unittest.main()
