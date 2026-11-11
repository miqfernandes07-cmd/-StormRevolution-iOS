"""Bounded, read-only XEX2 metadata inspector. No keys or decryption.

Format research: Xenia xex2_info.h / xex_module.cc (see docs/REFERENCES.md).
This is an independent implementation; reports never include image/key bytes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
import struct
import sys

MAX_FILE_SIZE = 512 * 1024 * 1024


class XexError(ValueError):
    pass


class Reader:
    def __init__(self, data: bytes):
        self.data = data

    def span(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset > len(self.data) - size:
            raise XexError(f'XEX_BOUNDS: offset=0x{offset:x} size=0x{size:x} limit=0x{len(self.data):x}')
        return self.data[offset:offset + size]

    def u32(self, offset: int) -> int:
        return struct.unpack('>I', self.span(offset, 4))[0]

    def u16(self, offset: int) -> int:
        return struct.unpack('>H', self.span(offset, 2))[0]


def version(value: int) -> str:
    # Packed version: major[31:28], minor[27:24], build[23:8], QFE[7:0].
    # Do not infer on-disk bit order from host C++ bitfield declaration order.
    return f'{value >> 28}.{(value >> 24) & 15}.{(value >> 8) & 65535}.{value & 255}'


def imports(data: bytes) -> list[dict]:
    r = Reader(data)
    string_size, string_count = r.u32(4), r.u32(8)
    strings = Reader(r.span(12, string_size))
    if string_count > string_size:
        raise XexError('XEX_IMPORT_NAMES: impossible string count')
    names, cursor = [], 0
    for _ in range(string_count):
        end = strings.data.find(b'\0', cursor)
        if end < 0:
            raise XexError('XEX_IMPORT_NAMES: unterminated library name')
        try:
            names.append(strings.span(cursor, end - cursor).decode('ascii'))
        except UnicodeDecodeError as exc:
            raise XexError('XEX_IMPORT_NAMES: non-ASCII library name') from exc
        cursor = (end + 4) & ~3
    cursor, result = 12 + string_size, []
    while cursor < len(data):
        size = r.u32(cursor)
        if size < 40:
            raise XexError('XEX_IMPORT_SIZE: library smaller than header')
        lib = Reader(r.span(cursor, size))
        index, count = lib.u16(36) & 255, lib.u16(38)
        if index >= len(names) or size != 40 + 4 * count:
            raise XexError('XEX_IMPORT_SIZE: invalid name index or record count')
        result.append({'name': names[index], 'id': lib.u32(24),
                       'version': version(lib.u32(28)),
                       'minimum_version': version(lib.u32(32)),
                       'record_addresses': [lib.u32(40 + 4 * i) for i in range(count)],
                       'ordinals_status': 'requires_loaded_image'})
        cursor += size
    return result


def inspect(data: bytes) -> dict:
    if len(data) > MAX_FILE_SIZE:
        raise XexError('XEX_SIZE_LIMIT: exceeds 512 MiB analysis budget')
    r = Reader(data)
    if r.span(0, 4) != b'XEX2':
        raise XexError('XEX_MAGIC: expected XEX2')
    r.span(0, 24)
    payload, security, count = r.u32(8), r.u32(16), r.u32(20)
    if payload < 24 or payload >= len(data):
        raise XexError('XEX_HEADER_SIZE: no image payload or invalid offset')
    h = Reader(r.span(0, payload))
    h.span(24, count * 8)
    table_end = 24 + count * 8
    if count > 4096:
        raise XexError('XEX_HEADER_COUNT_LIMIT: exceeds 4096 optional headers')
    report = {'schema_version': 1, 'format': 'XEX2', 'size_bytes': len(data),
              'sha1': hashlib.sha1(data).hexdigest(), 'sha256': hashlib.sha256(data).hexdigest(),
              'module_flags': r.u32(4), 'payload_offset': payload,
              'optional_headers': [], 'imports': [], 'diagnostics': [],
              'analysis': {'functions': 'not_implemented', 'jump_tables': 'not_implemented',
                           'instructions': 'requires_decoded_image',
                           'exports': 'requires_loaded_image',
                           'signature_verification': 'not_implemented'}}
    def diagnostic(code, message):
        report['diagnostics'].append({'code': code, 'message': message})
    entries = {}
    occupied = [(0, table_end)]
    def claim(offset, size):
        # Check before copying blocks, so overlapping aliases cannot amplify memory.
        if any(offset < end and offset + size > start for start, end in occupied):
            raise XexError('XEX_HEADER_OVERLAP: overlapping header structures')
        occupied.append((offset, offset + size))
    for i in range(count):
        key, value = h.u32(24 + i * 8), h.u32(28 + i * 8)
        if key in entries:
            raise XexError(f'XEX_DUPLICATE_HEADER: 0x{key:08x}')
        kind = key & 255
        entry = {'key': f'0x{key:08x}'}
        if kind <= 1:
            entry['value'] = value
            block = None
        else:
            if value < table_end:
                raise XexError('XEX_HEADER_OVERLAP: optional header intersects table')
            size = h.u32(value) if kind == 255 else kind * 4
            if kind == 255 and size < 4:
                raise XexError('XEX_OPTION_SIZE: variable header shorter than size field')
            claim(value, size)
            block = h.span(value, size)
            entry.update(offset=value, size=size)
        entries[key] = (value, block)
        report['optional_headers'].append(entry)
    if security < table_end:
        raise XexError('XEX_SECURITY_OFFSET: intersects main header')
    security_size = h.u32(security)
    if security_size < 0x184:
        raise XexError('XEX_SECURITY_SIZE: truncated fixed fields')
    claim(security, security_size)
    sec = Reader(h.span(security, security_size))
    image_size, flags, base = sec.u32(4), sec.u32(0x10c), sec.u32(0x110)
    if not image_size or image_size > 0x100000000 - base:
        raise XexError('XEX_IMAGE_SIZE: empty or exceeds guest address space')
    pages = sec.u32(0x180)
    sec.span(0x184, pages * 24)
    page_size, cursor, sections = (4096 if flags & 0x10000000 else 65536), base, []
    for i in range(pages):
        value = sec.u32(0x184 + 24 * i)
        kind, n = value & 15, value >> 4
        if not n or cursor + n * page_size > 0x100000000:
            raise XexError('XEX_PAGE_RANGE: empty or overflowing page range')
        sections.append({'address': cursor, 'size': n * page_size, 'type': kind,
                         'executable': kind == 1})
        cursor += n * page_size
    report['security'] = {'image_size': image_size, 'image_flags': flags,
                          'load_address': base, 'region_mask': sec.u32(0x178),
                          'allows_ntsc_u': bool(sec.u32(0x178) & 255),
                          'export_table_address': sec.u32(0x160),
                          'page_size': page_size, 'sections': sections}
    if cursor - base != ((image_size + page_size - 1) // page_size) * page_size:
        diagnostic('XEX_PAGE_COVERAGE', 'Page descriptors do not match rounded image size; inspect manually.')
    if 0x40006 in entries:
        e = Reader(entries[0x40006][1])
        report['execution'] = {'media_id': f'{e.u32(0):08X}', 'title_id': f'{e.u32(12):08X}',
                               'version_raw': f'0x{e.u32(4):08x}', 'version': version(e.u32(4)),
                               'base_version': version(e.u32(8)),
                               'platform': e.data[16], 'disc_number': e.data[18], 'disc_count': e.data[19]}
    else:
        diagnostic('XEX_NO_EXECUTION_INFO', 'Title and version cannot be validated.')
    for key, name in ((0x10100, 'entry_point'), (0x10201, 'image_base')):
        if key in entries:
            report[name] = entries[key][0]
    if 0x3ff in entries:
        fmt = Reader(entries[0x3ff][1])
        encryption, compression = fmt.u16(4), fmt.u16(6)
        report['file_format'] = {'encryption': encryption, 'compression': compression}
        if compression == 1:
            if len(fmt.data) < 16 or (len(fmt.data) - 8) % 8:
                raise XexError('XEX_BASIC_BLOCKS: expected complete data/zero block pairs')
            blocks = [{'data_size': fmt.u32(i), 'zero_size': fmt.u32(i + 4)}
                      for i in range(8, len(fmt.data), 8)]
            stored = sum(b['data_size'] for b in blocks)
            expanded = sum(b['data_size'] + b['zero_size'] for b in blocks)
            if stored > len(data) - payload:
                raise XexError('XEX_BASIC_PAYLOAD: blocks exceed available payload')
            if expanded != image_size:
                raise XexError('XEX_BASIC_IMAGE_SIZE: expanded blocks differ from security image size')
            report['file_format'].update(basic_blocks=blocks, stored_bytes=stored,
                zero_fill_bytes=expanded - stored, expanded_bytes=expanded,
                payload_trailing_bytes=len(data) - payload - stored)
        if encryption or compression:
            diagnostic('XEX_ENCODED_IMAGE', 'Metadata only: decryption/decompression not implemented; no keys are included.')
        else:
            diagnostic('XEX_IMAGE_ANALYSIS_PENDING', 'Plain payload present; PE sections, exports and PPC analysis not implemented here.')
    else:
        diagnostic('XEX_NO_FILE_FORMAT', 'Image encoding unknown.')
    if 0x103ff in entries:
        report['imports'] = imports(entries[0x103ff][1])
    return report


def validate(report: dict, reference: dict) -> dict:
    if not isinstance(reference, dict):
        raise XexError('XEX_REFERENCE_SCHEMA: expected an object')
    patterns = {'sha1': r'[0-9a-f]{40}', 'title_id': r'[0-9A-F]{8}',
                'media_id': r'[0-9A-F]{8}', 'version': r'\d+\.\d+\.\d+\.\d+'}
    for key, pattern in patterns.items():
        if not isinstance(reference.get(key), str) or not re.fullmatch(pattern, reference[key]):
            raise XexError(f'XEX_REFERENCE_SCHEMA: missing or invalid {key}')
    if type(reference.get('size_bytes')) is not int or not 0 < reference['size_bytes'] <= MAX_FILE_SIZE:
        raise XexError('XEX_REFERENCE_SCHEMA: invalid size_bytes')
    actual = {'sha1': report['sha1'], 'size_bytes': report['size_bytes'],
              'title_id': report.get('execution', {}).get('title_id'),
              'media_id': report.get('execution', {}).get('media_id'),
              'version': report.get('execution', {}).get('version')}
    checks = {k: {'expected': reference[k], 'actual': v, 'match': reference[k] == v}
              for k, v in actual.items() if reference.get(k) is not None}
    # Region is an eligibility mask, not a unique disc-region identifier.
    checks['ntsc_u_eligible'] = {'expected': True, 'actual': report['security']['allows_ntsc_u'],
                                'match': report['security']['allows_ntsc_u']}
    return {'reference_source': reference.get('source'), 'checks': checks,
            'matches_reference': all(c['match'] for c in checks.values()),
            'boot_compatibility': 'unknown'}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('xex', type=Path)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--output', type=Path, help='Keep original-game reports under private/.')
    args = parser.parse_args(argv)
    try:
        if args.output:
            for source in (args.xex, args.reference):
                if source and (args.output.resolve() == source.resolve() or
                               (args.output.exists() and source.exists() and args.output.samefile(source))):
                    raise XexError('XEX_OUTPUT_OVERWRITES_INPUT: report must differ from source/reference')
        # Read at most limit+1 even if the file changes after stat.
        with args.xex.open('rb') as stream:
            report = inspect(stream.read(MAX_FILE_SIZE + 1))
        if args.reference:
            report['validation'] = validate(report, json.loads(args.reference.read_text()))
        output = json.dumps(report, indent=2) + '\n'
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output)
        else:
            print(output, end='')
        return 2 if report.get('validation', {}).get('matches_reference') is False else 0
    except (OSError, XexError, json.JSONDecodeError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
