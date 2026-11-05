"""Synthetic PPC words are authored here; no original game code is needed."""
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ppc_aot", ROOT / "tools/recompilation/ppc_aot.py")
AOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AOT)
BLR = 0x4E800020


def words(*values):
    return b"".join(struct.pack(">I", value) for value in values)


def d(opcode, rt, ra, immediate):
    return (opcode << 26) | (rt << 21) | (ra << 16) | (immediate & 0xFFFF)


def x(xo, rt, ra, rb):
    return (31 << 26) | (rt << 21) | (ra << 16) | (rb << 11) | (xo << 1)


class TestAOT(unittest.TestCase):
    def test_native_execution(self):
        # RA=0 ignores nonzero r0 for addi, but ori reads r0 normally.
        binary = words(d(14, 3, 0, -1), d(14, 4, 3, 1), d(15, 5, 0, -32768),
                       d(24, 0, 6, 0xABCD), x(266, 7, 3, 3), x(444, 8, 9, 6),
                       (18 << 26) | 8, d(14, 10, 0, 99), d(14, 11, 0, -32768), BLR)
        source, report = AOT.translate(binary)
        self.assertEqual(report["instructions"]["b"], 1)
        compiler = shlex.split(os.environ.get("CXX", "c++"))
        self.assertTrue(shutil.which(compiler[0]), "Native C++ compiler is required for AOT execution test")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "generated.cpp").write_text(source)
            (path / "main.cpp").write_text('''
#include <cassert>
#include <cstdint>
#include "runtime/cpu/context.h"
void synthetic_entry(storm::cpu::Context&);
int main() {
    storm::cpu::Context ctx;
    ctx.gpr[0] = UINT64_C(0x100000000);
    ctx.gpr[8] = 0x1000;
    ctx.gpr[10] = 7;
    synthetic_entry(ctx);
    assert(ctx.gpr[3] == UINT64_MAX);
    assert(ctx.gpr[4] == 0);
    assert(ctx.gpr[5] == UINT64_C(0xFFFFFFFF80000000));
    assert(ctx.gpr[6] == UINT64_C(0x10000ABCD));
    assert(ctx.gpr[7] == UINT64_MAX - 1);
    assert(ctx.gpr[9] == UINT64_C(0x10000BBCD));
    assert(ctx.gpr[10] == 7);
    assert(ctx.gpr[11] == UINT64_C(0xFFFFFFFFFFFF8000));
}
''')
            build = subprocess.run(compiler + ["-std=c++17", "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined", "-I", str(ROOT), str(path / "generated.cpp"), str(path / "main.cpp"), "-o", str(path / "native")], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(path / "native")], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stderr, "", "UBSan reported undefined behavior")

    def test_unknown_word_has_address(self):
        with self.assertRaises(AOT.TranslationError) as caught:
            AOT.translate(words(d(14, 1, 0, 1), 0, BLR))
        self.assertEqual(caught.exception.diagnostic()["address"], "0x82000004")
        self.assertEqual(caught.exception.code, "PPC_UNSUPPORTED")

    def test_unreachable_unknown_rejected(self):
        with self.assertRaises(AOT.TranslationError):
            AOT.translate(words((18 << 26) | 8, 0, BLR))

    def test_variant_flags_rejected(self):
        for instruction in (x(266, 1, 2, 3) | 1, x(266, 1, 2, 3) | 0x400,
                            x(444, 1, 2, 3) | 1, (18 << 26) | 9,
                            (18 << 26) | 10):
            with self.subTest(instruction=hex(instruction)), self.assertRaises(AOT.TranslationError):
                AOT.translate(words(instruction, BLR))

    def test_branch_limits(self):
        for instruction in ((18 << 26), (18 << 26) | 0x03FFFFFC, (18 << 26) | 8):
            with self.subTest(instruction=hex(instruction)), self.assertRaises(AOT.TranslationError) as caught:
                AOT.translate(words(instruction, BLR))
            self.assertEqual(caught.exception.code, "AOT_UNSUPPORTED_BRANCH")

    def test_missing_return_and_bad_ranges(self):
        for binary, base in ((b"", 0), (b"\x00", 0), (words(BLR), 1),
                             (words(BLR, BLR), 0xFFFFFFFC), (words(d(14, 1, 0, 1)), 0)):
            with self.subTest(binary=binary, base=base), self.assertRaises(AOT.TranslationError):
                AOT.translate(binary, base=base)

    def test_invalid_symbol(self):
        with self.assertRaises(AOT.TranslationError):
            AOT.translate(words(BLR), function="foo;system(0)")

    def test_cli_cannot_overwrite_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.ppc'
            original = words(BLR)
            path.write_bytes(original)
            alias = Path(directory) / 'alias.ppc'
            alias.hardlink_to(path)
            for output in (path, alias):
                run = subprocess.run([os.sys.executable, str(ROOT / 'tools/recompilation/ppc_aot.py'),
                                      str(path), str(output)], capture_output=True, text=True)
                self.assertEqual(run.returncode, 2)
                self.assertEqual(json.loads(run.stderr)['code'], 'AOT_PATH_COLLISION')
                self.assertEqual(path.read_bytes(), original)

    def test_cli_failure_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "input.bin").write_bytes(words(0, BLR))
            run = subprocess.run([os.sys.executable, str(ROOT / "tools/recompilation/ppc_aot.py"), str(path / "input.bin"), str(path / "output.cpp")], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(json.loads(run.stderr)["code"], "PPC_UNSUPPORTED")
            self.assertFalse((path / "output.cpp").exists())


if __name__ == "__main__":
    unittest.main()
