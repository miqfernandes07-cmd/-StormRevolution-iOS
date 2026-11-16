"""Synthetic PE fixtures and independently assembled PPC instruction sequences."""
import importlib.util
from pathlib import Path
import struct
import unittest
from test_pe import PE, fixture, BASE

SPEC = importlib.util.spec_from_file_location('abi_helpers', Path(__file__).resolve().parents[1]/'tools/ppc_analysis/abi_helpers.py')
ABI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ABI)


def helper(restore=False):
    # std/ld r14..r31, -152..-16(r1), followed by LR store/load and return.
    data = bytearray()
    for reg in range(14, 32):
        op = 62 if not restore else 58
        data += struct.pack('>I', (op << 26) | (reg << 21) | (1 << 16) | ((8*reg-264) & 0xffff))
    data += bytes.fromhex('8181fff87d8803a64e800020' if restore else '9181fff84e800020')
    return data


class AbiHelperTests(unittest.TestCase):
    def test_unique_helpers_in_both_layouts(self):
        for layout in ('file', 'mapped'):
            data = fixture(layout)
            pe = PE.PEImage(data, layout)
            offset = 0x1000 if layout == 'mapped' else pe.sections[0]['raw_offset']
            data[offset:offset+80] = helper()
            data[offset+0x80:offset+0x80+84] = helper(True)
            report = ABI.discover(PE.PEImage(data, layout))
            self.assertEqual(report['helpers']['savegprlr_14_address']['address'], BASE+0x1000)
            self.assertEqual(report['helpers']['restgprlr_14_address']['address'], BASE+0x1080)
            self.assertFalse(report['game_execution_approved'])

    def test_duplicate_or_absent_is_never_selected(self):
        data = fixture('mapped')
        data[0x1000:0x1050] = helper()
        data[0x1080:0x10d0] = helper()
        report = ABI.discover(PE.PEImage(data, 'mapped'))['helpers']
        self.assertEqual(len(report['savegprlr_14_address']['candidates']), 2)
        self.assertIsNone(report['savegprlr_14_address']['address'])
        self.assertIsNone(report['restgprlr_14_address']['address'])

    def test_wrong_register_offset_return_alignment_or_permissions(self):
        for change in ('register', 'offset', 'return', 'unaligned', 'noncode', 'truncated'):
            data = fixture('mapped'); pattern = helper()
            if change == 'register': pattern[1] ^= 32
            if change == 'offset': pattern[3] ^= 8
            if change == 'return': pattern[-1] ^= 1
            if change == 'truncated': pattern = pattern[:-4]
            start = 0x1001 if change == 'unaligned' else 0x1000
            data[start:start+len(pattern)] = pattern
            image = PE.PEImage(data, 'mapped')
            if change == 'noncode': image.sections[0]['executable'] = False
            self.assertIsNone(ABI.discover(image)['helpers']['savegprlr_14_address']['address'], change)
        image.machine = 0x14c
        with self.assertRaisesRegex(ValueError, 'MACHINE'): ABI.discover(image)
