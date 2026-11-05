#!/usr/bin/env python3
"""Strict, synthetic PPC AOT bring-up subset; not the game's recompiler.

Only straight-line integer operations, forward intra-block branches and a final
blr are supported. Every input word is validated, including unreachable words.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import struct
import sys


class TranslationError(ValueError):
    def __init__(self, code: str, message: str, address: int | None = None,
                 word: int | None = None):
        super().__init__(message)
        self.code, self.address, self.word = code, address, word

    def diagnostic(self) -> dict:
        return {"code": self.code, "message": str(self),
                "address": None if self.address is None else f"0x{self.address:08X}",
                "instruction": None if self.word is None else f"0x{self.word:08X}"}


def _signed(value: int, bits: int) -> int:
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def translate(data: bytes, base: int = 0x82000000,
              function: str = "synthetic_entry") -> tuple[str, dict]:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", function) or function.startswith("_"):
        raise TranslationError("AOT_INVALID_SYMBOL", "Expected a non-reserved C++ identifier")
    if not 0 <= base <= 0xFFFFFFFF or base % 4:
        raise TranslationError("AOT_INVALID_BASE", "Base must be aligned unsigned 32-bit address")
    if not data or len(data) % 4 or len(data) > 1024 * 1024:
        raise TranslationError("AOT_INVALID_SIZE", "Input must contain 1..262144 complete PPC words")
    if base + len(data) > 0x100000000:
        raise TranslationError("AOT_ADDRESS_OVERFLOW", "Guest address range exceeds 32 bits")
    words = [word for (word,) in struct.iter_unpack(">I", data)]
    emitted: list[str] = []
    counts: dict[str, int] = {}
    branch_targets: set[int] = set()
    for index, word in enumerate(words):
        pc = base + index * 4
        opcode = word >> 26
        rt, ra, rb = (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
        mnemonic, line = "", ""
        if word == 0x4E800020:
            mnemonic, line = "blr", "return;"
        elif opcode in (14, 15):
            mnemonic = "addi" if opcode == 14 else "addis"
            immediate = _signed(word & 0xFFFF, 16) * (1 if opcode == 14 else 65536)
            # Convert the signed immediate modulo 2^64 ahead of compilation.
            rhs = immediate & 0xFFFFFFFFFFFFFFFF
            lhs = f"ctx.gpr[{ra}]" if ra else "UINT64_C(0)"
            line = f"ctx.gpr[{rt}] = {lhs} + UINT64_C({rhs});"
        elif opcode == 24:
            mnemonic = "ori"
            line = f"ctx.gpr[{ra}] = ctx.gpr[{rt}] | UINT64_C({word & 0xFFFF});"
        elif opcode == 31 and ((word >> 1) & 1023) in (266, 444) and not (word & 1):
            xo = (word >> 1) & 1023
            if xo == 266:
                mnemonic = "add"
                line = f"ctx.gpr[{rt}] = ctx.gpr[{ra}] + ctx.gpr[{rb}];"
            else:
                mnemonic = "or"
                line = f"ctx.gpr[{ra}] = ctx.gpr[{rt}] | ctx.gpr[{rb}];"
        elif opcode == 18 and not word & 3:
            target = pc + _signed(word & 0x03FFFFFC, 26)
            if target <= pc or target >= base + len(data):
                raise TranslationError("AOT_UNSUPPORTED_BRANCH", "Only forward in-block relative b is supported", pc, word)
            mnemonic = "b"
            branch_targets.add(target)
            line = f"goto pc_{target:08x};"
        else:
            raise TranslationError("PPC_UNSUPPORTED", "Instruction or flag variant is not implemented", pc, word)
        emitted.append(line)
        counts[mnemonic] = counts.get(mnemonic, 0) + 1
    if words[-1] != 0x4E800020:
        raise TranslationError("AOT_MISSING_RETURN", "Synthetic function must end with exact blr", base + len(data) - 4, words[-1])
    lines = ['// Generated from PPC input. No runtime instruction decoding.',
             '#include <cstdint>', '#include "runtime/cpu/context.h"',
             f'void {function}(storm::cpu::Context& ctx) {{', '  (void)ctx;']
    for index, line in enumerate(emitted):
        pc = base + index * 4
        if pc in branch_targets:
            lines.append(f'pc_{pc:08x}:')
        lines.append(f'  {line} // 0x{pc:08X}: 0x{words[index]:08X}')
    lines.append('}')
    return '\n'.join(lines) + '\n', {
        "format": "synthetic-ppc-aot-v1", "base_address": f"0x{base:08X}",
        "word_count": len(words), "instructions": counts,
        "supported_only": True, "xenonrecomp_integrated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--base", type=lambda text: int(text, 0), default=0x82000000)
    parser.add_argument("--function", default="synthetic_entry")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        paths = [args.input, args.output] + ([args.report] if args.report else [])
        for index, left in enumerate(paths):
            for right in paths[index + 1:]:
                if left.resolve() == right.resolve() or (left.exists() and right.exists() and left.samefile(right)):
                    raise TranslationError('AOT_PATH_COLLISION', 'Input, C++ output and report must be different files')
        # Bound the read before parsing: a malformed or unexpectedly large input
        # must not allocate the entire file. Existing output is left untouched on
        # failure; callers must check the exit status and never reuse it as proof.
        with args.input.open("rb") as input_file:
            source, report = translate(input_file.read(1024 * 1024 + 1), args.base, args.function)
        args.output.write_text(source, encoding="utf-8")
        if args.report:
            args.report.write_text(json.dumps(report, indent=2) + '\n', encoding="utf-8")
    except TranslationError as error:
        print(json.dumps(error.diagnostic()), file=sys.stderr)
        return 2
    except OSError as error:
        print(json.dumps({"code": "AOT_IO_ERROR", "message": str(error)}), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
