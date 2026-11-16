#!/usr/bin/env python3
"""Locate exact PPC64 GPR/LR save/restore sequences; no title execution approval."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('helper_pe', ROOT/'tools/xex_analysis/pe.py')
PE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PE)


def sequence(restore):
    opcode = 0xe8000000 if restore else 0xf8000000
    words = [opcode | register << 21 | 1 << 16 | ((-152 + (register-14)*8) & 65535)
             for register in range(14, 32)]
    words += [0x8181fff8, 0x7d8803a6, 0x4e800020] if restore else [0x9181fff8, 0x4e800020]
    return b''.join(struct.pack('>I', word) for word in words)


def discover(image):
    if image.machine != 0x1f2:
        raise ValueError('ABI_HELPER_MACHINE: Xbox PowerPC PE required')
    result = {}
    for restore, name in ((False, 'savegprlr_14_address'), (True, 'restgprlr_14_address')):
        pattern = sequence(restore)
        matches = []
        for section in image.sections:
            if not section['executable']:
                continue
            # File layouts have no stored bytes for BSS tails.
            size = section['mapped_extent'] if image.layout == 'mapped' else section['raw_size']
            raw = image.rva_bytes(section['rva'], size)
            start = 0
            while (offset := raw.find(pattern, start)) >= 0:
                address = section['address'] + offset
                if address % 4 == 0:
                    matches.append(address)
                start = offset + 1
        result[name] = {'candidates': matches, 'unique': len(matches) == 1,
                        'address': matches[0] if len(matches) == 1 else None}
    return {'helpers': result, 'game_execution_approved': False,
            'scope': 'exact_gpr_lr_sequences_only; other_helpers_and_ABI_unqualified'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--layout', choices=('mapped', 'file'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.image.open('rb') as stream:
            data = stream.read(512*1024*1024 + 1)
        if len(data) > 512*1024*1024:
            raise ValueError('ABI_HELPER_IMAGE_SIZE')
        report = discover(PE.PEImage(data, args.layout))
        report['image_sha256'] = hashlib.sha256(data).hexdigest()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
        print(json.dumps(report))
        return 0
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
