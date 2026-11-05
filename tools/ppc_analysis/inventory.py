#!/usr/bin/env python3
"""Bounded static inventory of an explicitly selected raw big-endian PPC region.

Not a complete disassembler, PE loader or encrypted-XEX decoder. Every aligned
word is scanned, including unreachable words/data. Known branch operands yield
references and function candidates, never proven function boundaries.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

MAX_REGION_SIZE = 1024 * 1024
ADDRESS_SPACE = 1 << 32


class InventoryError(ValueError):
    pass


def signed(value: int, bits: int) -> int:
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def address(value: int) -> str:
    return f'0x{value:08X}'


def classify(word: int) -> tuple[str | None, str | None]:
    """This taxonomy does not assert the synthetic or Xenon recompiler supports it."""
    if word in (0x4E800020, 0x4E800420, 0x4E800421):
        return {0x4E800020: 'blr', 0x4E800420: 'bctr', 0x4E800421: 'bctrl'}[word], None
    opcode = word >> 26
    if opcode in (14, 15, 24, 18, 16):
        return {14: 'addi', 15: 'addis', 24: 'ori', 18: 'b', 16: 'bc'}[opcode], None
    if opcode == 31:
        xo = (word >> 1) & 1023
        if xo == 266 and not word & 1:
            return 'add', None
        if xo == 444 and not word & 1:
            return 'or', None
        if (xo & 511) == 266 or xo == 444:
            return None, 'PPC_INVENTORY_UNSUPPORTED_VARIANT'
    if opcode == 19 and ((word >> 1) & 1023) in (16, 528):
        return None, 'PPC_INVENTORY_UNSUPPORTED_INDIRECT_VARIANT'
    return None, 'PPC_INVENTORY_UNKNOWN'


def synthetic_aot_check(data: bytes, base: int) -> dict:
    """Use the actual current translator, rather than duplicate its coverage rules."""
    path = Path(__file__).resolve().parents[1] / 'recompilation/ppc_aot.py'
    spec = importlib.util.spec_from_file_location('storm_inventory_aot', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        _, report = module.translate(data, base=base)
        return {'accepted': True, 'scope': 'synthetic_translator_only', 'report': report,
                'compiled': False, 'executed': False}
    except module.TranslationError as error:
        return {'accepted': False, 'scope': 'synthetic_translator_only',
                'first_diagnostic': error.diagnostic(), 'compiled': False, 'executed': False}


def inventory(data: bytes, base: int, entry: int | None = None) -> dict:
    if type(base) is not int or not 0 <= base < ADDRESS_SPACE or base % 4:
        raise InventoryError('PPC_INVENTORY_BASE: expected aligned unsigned 32-bit address')
    if not data or len(data) % 4 or len(data) > MAX_REGION_SIZE:
        raise InventoryError('PPC_INVENTORY_SIZE: expected 1..262144 complete big-endian words')
    if base + len(data) > ADDRESS_SPACE:
        raise InventoryError('PPC_INVENTORY_RANGE: input region must not wrap the guest address space')
    # XEX2 may be aligned raw bytes, but cannot legitimately be this input format.
    if data[:4] in (b'XEX2', b'XEX1'):
        raise InventoryError('PPC_INVENTORY_CONTAINER: extract executable bytes before raw analysis')
    end = base + len(data)
    if entry is None:
        entry = base
    if type(entry) is not int or entry % 4 or not base <= entry < end:
        raise InventoryError('PPC_INVENTORY_ENTRY: entry must be an aligned address inside the region')
    histogram: Counter[str] = Counter()
    diagnostics, references, indirect, edges = [], [], [], []
    candidates: dict[int, set[str]] = {entry: {'selected_entry'}}
    known = 0
    for index, (word,) in enumerate(struct.iter_unpack('>I', data)):
        pc = base + index * 4
        mnemonic, error = classify(word)
        if error:
            histogram['unknown'] += 1
            diagnostics.append({'code': error, 'address': address(pc), 'word': address(word),
                                'primary_opcode': word >> 26,
                                'message': 'Not decoded by this inventory; no instruction semantics inferred.'})
            continue
        known += 1
        histogram[mnemonic] += 1
        if mnemonic in ('b', 'bc'):
            displacement = signed(word & (0x03FFFFFC if mnemonic == 'b' else 0xFFFC),
                                  26 if mnemonic == 'b' else 16)
            absolute, link = bool(word & 2), bool(word & 1)
            unwrapped = displacement if absolute else pc + displacement
            target = unwrapped & 0xFFFFFFFF
            in_region = base <= target < end
            # AA is a sign-extended absolute address. For relative branches report
            # arithmetic wrap separately; there is no host pointer arithmetic here.
            reference = {'source': address(pc), 'target': address(target),
                         'mnemonic': mnemonic, 'absolute': absolute, 'link': link,
                         'displacement': displacement, 'target_in_region': in_region,
                         'relative_address_wrapped': not absolute and not 0 <= unwrapped < ADDRESS_SPACE}
            if mnemonic == 'bc':
                reference.update(bo=(word >> 21) & 31, bi=(word >> 16) & 31,
                                 condition_evaluation='not_implemented')
            references.append(reference)
            edges.append({'source': address(pc), 'target': address(target),
                          'kind': 'possible_call' if link else ('branch' if mnemonic == 'b' else 'possible_branch'),
                          'target_in_region': in_region})
            if link:
                candidates.setdefault(target, set()).add('direct_link_target')
            if mnemonic == 'bc' or link:
                continuation = (pc + 4) & 0xFFFFFFFF
                edges.append({'source': address(pc), 'target': address(continuation),
                              'kind': 'possible_call_continuation' if link else 'possible_fallthrough',
                              'target_in_region': base <= continuation < end})
        elif mnemonic in ('blr', 'bctr', 'bctrl'):
            indirect.append({'address': address(pc), 'mnemonic': mnemonic,
                             'target_register': 'lr' if mnemonic == 'blr' else 'ctr',
                             'target_resolution': 'not_implemented',
                             'interpretation': 'possible_return' if mnemonic == 'blr' else 'indirect_branch'})
            if mnemonic == 'bctrl':
                continuation = (pc + 4) & 0xFFFFFFFF
                edges.append({'source': address(pc), 'target': address(continuation),
                              'kind': 'possible_call_continuation', 'target_in_region': base <= continuation < end})
        else:
            continuation = (pc + 4) & 0xFFFFFFFF
            edges.append({'source': address(pc), 'target': address(continuation), 'kind': 'fallthrough',
                          'target_in_region': base <= continuation < end})
    return {'schema_version': 1, 'input_format': 'raw-ppc-big-endian-explicit',
            'base_address': address(base), 'end_address_exclusive': f'0x{end:X}',
            'entry_address': address(entry), 'size_bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(), 'word_count': len(data) // 4,
            'known_word_count': known, 'unknown_word_count': len(data) // 4 - known,
            'instruction_histogram': dict(sorted(histogram.items())),
            'branch_references': references, 'control_flow_edges': edges,
            'indirect_branches': indirect,
            'function_candidates': [{'address': address(pc), 'reasons': sorted(reasons),
                                     'in_region': base <= pc < end, 'boundary_verified': False}
                                    for pc, reasons in sorted(candidates.items())],
            'diagnostics': diagnostics,
            'analysis_status': {'function_boundaries': 'not_implemented',
                                'jump_table_recovery': 'not_implemented',
                                'indirect_target_recovery': 'not_implemented',
                                'code_data_separation': 'caller_supplied_not_verified',
                                'reachability': 'not_implemented',
                                'branch_conditions': 'not_evaluated',
                                'bc_bo_legality': 'not_verified',
                                'xenonrecomp_coverage': 'not_measured',
                                'xex_pe_decoding': 'not_implemented'},
            'synthetic_aot_check': synthetic_aot_check(data, base)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-ppc', required=True, type=Path,
                        help='Explicit raw executable region, not default.xex or encrypted payload.')
    parser.add_argument('--base', required=True, type=lambda value: int(value, 0))
    parser.add_argument('--entry', type=lambda value: int(value, 0))
    parser.add_argument('--output', type=Path, help='Keep game-derived reports in private/.')
    args = parser.parse_args(argv)
    try:
        if args.output and (args.output.resolve() == args.raw_ppc.resolve()
                            or (args.output.exists() and args.output.samefile(args.raw_ppc))):
            raise InventoryError('PPC_INVENTORY_OUTPUT: report must not overwrite input')
        with args.raw_ppc.open('rb') as source:
            report = inventory(source.read(MAX_REGION_SIZE + 1), args.base, args.entry)
        text = json.dumps(report, indent=2) + '\n'
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding='utf-8')
        else:
            print(text, end='')
        # Unknown forms are a visible nonzero outcome, but preserve the useful report.
        return 2 if report['unknown_word_count'] else 0
    except (OSError, InventoryError) as error:
        print(json.dumps({'code': 'PPC_INVENTORY_ERROR', 'message': str(error)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
