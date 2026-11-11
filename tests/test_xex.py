"""Entirely synthetic XEX containers, never commercial bytes."""
import importlib.util
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('xex', ROOT / 'tools/xex_analysis/xex.py')
xex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xex)


def fixture():
    data = bytearray(0x404)
    def word(off, value):
        struct.pack_into('>I', data, off, value)
    data[:4] = b'XEX2'
    word(4, 1)
    word(8, 0x400)
    word(16, 0x200)
    word(20, 5)
    for i, (k, v) in enumerate([(0x40006, 0x60), (0x3ff, 0x78),
                                (0x10100, 0x82000000), (0x10201, 0x82000000), (0x103ff, 0x80)]):
        word(24 + i * 8, k)
        word(28 + i * 8, v)
    word(0x60, 0x29e320a9)
    word(0x64, 0x00000004)
    word(0x6c, 0x4e4d0868)
    data[0x70:0x74] = bytes([2, 0, 1, 1])
    word(0x78, 8)
    strings = b'xboxkrnl.exe\0\0\0\0'
    word(0x80, 12 + len(strings) + 44)
    word(0x84, len(strings))
    word(0x88, 1)
    data[0x8c:0x8c + len(strings)] = strings
    lib = 0x8c + len(strings)
    word(lib, 44)
    word(lib + 28, 0x00010002)
    struct.pack_into('>H', data, lib + 38, 1)
    word(lib + 40, 0x82000100)
    word(0x200, 0x19c)
    word(0x204, 0x10000)
    word(0x310, 0x82000000)
    word(0x378, 0xff)
    word(0x380, 1)
    word(0x384, 0x11)
    data[0x400:] = bytes.fromhex('4e800020')
    return data


class XexTests(unittest.TestCase):
    def test_metadata(self):
        report = xex.inspect(fixture())
        self.assertEqual(report['execution']['version'], '0.0.0.4')
        self.assertEqual(report['execution']['title_id'], '4E4D0868')
        self.assertEqual(report['entry_point'], 0x82000000)
        self.assertEqual(report['security']['sections'], [dict(address=0x82000000, size=65536, type=1, executable=True)])
        self.assertEqual(report['imports'][0]['name'], 'xboxkrnl.exe')
        self.assertEqual(report['imports'][0]['record_addresses'], [0x82000100])
        self.assertEqual(report['analysis']['instructions'], 'requires_decoded_image')
        self.assertNotIn('aes_key', json.dumps(report))

    def test_every_truncation(self):
        data = fixture()
        for n in range(0x401):
            with self.subTest(length=n), self.assertRaises(xex.XexError):
                xex.inspect(data[:n])

    def test_bad_magic(self):
        with self.assertRaisesRegex(xex.XexError, 'XEX_MAGIC'):
            xex.inspect(b'NOPE' + bytes(64))

    def test_version_bits(self):
        self.assertEqual(xex.version(0x12abcd43), '1.2.43981.67')
        self.assertEqual(xex.version(4), '0.0.0.4')
        self.assertEqual(xex.version(0x04000000), '0.4.0.0')

    def test_encoded_image_not_reported_as_analyzed(self):
        data = fixture()
        struct.pack_into('>HH', data, 0x7c, 1, 2)
        report = xex.inspect(data)
        self.assertIn('XEX_ENCODED_IMAGE', [d['code'] for d in report['diagnostics']])
        self.assertEqual(report['analysis']['exports'], 'requires_loaded_image')

    def test_duplicate(self):
        data = fixture()
        struct.pack_into('>I', data, 32, 0x40006)
        with self.assertRaisesRegex(xex.XexError, 'XEX_DUPLICATE'):
            xex.inspect(data)

    def test_basic_compression_sizes(self):
        data = fixture()
        struct.pack_into('>I', data, 36, 0x100)
        struct.pack_into('>IHHII', data, 0x100, 16, 0, 1, 4, 65532)
        result = xex.inspect(data)['file_format']
        self.assertEqual(result['stored_bytes'], 4)
        self.assertEqual(result['zero_fill_bytes'], 65532)
        self.assertEqual(result['expanded_bytes'], 65536)
        for offset, value, code in ((0x100, 12, 'XEX_BASIC_BLOCKS'),
                                    (0x108, 8, 'XEX_BASIC_PAYLOAD'),
                                    (0x10c, 1, 'XEX_BASIC_IMAGE_SIZE')):
            changed = bytearray(data)
            struct.pack_into('>I', changed, offset, value)
            with self.subTest(code=code), self.assertRaisesRegex(xex.XexError, code):
                xex.inspect(changed)

    def test_invalid_offsets_and_counts(self):
        for off, value in [(8, 0), (8, 0xffffffff), (16, 0), (20, 0xffffffff),
                           (28, 0xfffffff0), (0x78, 3), (0x200, 4),
                           (0x380, 0xffffffff), (0x384, 1), (0x84, 0xffffffff),
                           (0x9c, 0), (0x204, 0xffffffff)]:
            with self.subTest(offset=off, value=value):
                data = fixture()
                struct.pack_into('>I', data, off, value)
                with self.assertRaises(xex.XexError):
                    xex.inspect(data)

    def test_overlap(self):
        data = fixture()
        struct.pack_into('>I', data, 36, 0x60)
        with self.assertRaises(xex.XexError):
            xex.inspect(data)

    def test_malformed_import_name(self):
        data = fixture()
        data[0x8c:0x9c] = b'A' * 16
        with self.assertRaisesRegex(xex.XexError, 'XEX_IMPORT_NAMES'):
            xex.inspect(data)

    def test_region_is_mask(self):
        data = fixture()
        struct.pack_into('>I', data, 0x378, 0xffffffff)
        self.assertTrue(xex.inspect(data)['security']['allows_ntsc_u'])
        struct.pack_into('>I', data, 0x378, 0xff00)
        self.assertFalse(xex.inspect(data)['security']['allows_ntsc_u'])

    def test_reference_rejects_synthetic_hash(self):
        reference = json.loads((ROOT / 'config/game_reference.json').read_text())
        validation = xex.validate(xex.inspect(fixture()), reference)
        self.assertFalse(validation['matches_reference'])
        self.assertTrue(validation['checks']['title_id']['match'])
        self.assertFalse(validation['checks']['sha1']['match'])
        self.assertFalse(validation['checks']['size_bytes']['match'])
        self.assertEqual(validation['boot_compatibility'], 'unknown')

    def test_invalid_reference_schema(self):
        for reference in ({}, [], None, {'sha1': 'not-a-hash'}):
            with self.subTest(reference=reference), self.assertRaisesRegex(xex.XexError, 'XEX_REFERENCE_SCHEMA'):
                xex.validate(xex.inspect(fixture()), reference)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, output = Path(tmp) / 'synthetic.xex', Path(tmp) / 'report.json'
            path.write_bytes(fixture())
            args = [sys.executable, str(ROOT / 'tools/xex_analysis/xex.py'), str(path), '--output', str(output)]
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertTrue(output.exists())
            self.assertEqual(subprocess.run(args + ['--reference', str(ROOT / 'config/game_reference.json')], capture_output=True).returncode, 2)
            path.write_bytes(b'bad')
            bad = subprocess.run(args, capture_output=True)
            self.assertEqual(bad.returncode, 1)
            self.assertIn(b'XEX_BOUNDS', bad.stderr)

    def test_cli_cannot_overwrite_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input.xex'
            original = bytes(fixture())
            path.write_bytes(original)
            alias = Path(tmp) / 'alias.xex'
            alias.hardlink_to(path)
            for output in (path, alias):
                run = subprocess.run([sys.executable, str(ROOT / 'tools/xex_analysis/xex.py'),
                                      str(path), '--output', str(output)], capture_output=True)
                self.assertEqual(run.returncode, 1)
                self.assertIn(b'XEX_OUTPUT_OVERWRITES_INPUT', run.stderr)
                self.assertEqual(path.read_bytes(), original)

    def test_seeded_mutations_never_escape_as_struct_errors(self):
        rng = random.Random(360)
        for _ in range(500):
            data = fixture()
            off = rng.randrange(len(data) - 3)
            data[off:off + 4] = rng.getrandbits(32).to_bytes(4, 'big')
            try:
                xex.inspect(data)
            except xex.XexError:
                pass


if __name__ == '__main__':
    unittest.main()
