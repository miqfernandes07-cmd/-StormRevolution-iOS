"""Bounded PE32 metadata and XEX import-slot analysis of a decoded image.

PE headers are little-endian; XEX import slots and PPC instructions are big-endian.
Explicit file/mapped layout is required. This module does not decode encrypted XEX.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys

MAX_IMAGE_SIZE = 512 * 1024 * 1024
MAX_IMPORT_RECORDS = 262144


class PEError(ValueError):
    pass


class PEImage:
    def __init__(self, data: bytes, layout: str):
        if layout not in ('file', 'mapped'):
            raise PEError('PE_LAYOUT: explicitly select file or mapped')
        if not data or len(data) > MAX_IMAGE_SIZE:
            raise PEError('PE_SIZE_LIMIT: image must be 1..512 MiB')
        self.data, self.layout = data, layout
        if self.span(0, 2) != b'MZ':
            raise PEError('PE_DOS_MAGIC: decoded PE image must start with MZ')
        nt = self.u32(0x3c)
        if nt < 64 or self.span(nt, 4) != b'PE\0\0':
            raise PEError('PE_NT_SIGNATURE: invalid NT header')
        self.machine, count = self.u16(nt + 4), self.u16(nt + 6)
        optional_size = self.u16(nt + 20)
        if not 1 <= count <= 96:
            raise PEError('PE_SECTION_COUNT: expected 1..96 sections')
        if optional_size < 96:
            raise PEError('PE_OPTIONAL_SIZE: PE32 fields are truncated')
        opt = nt + 24
        self.span(opt, optional_size)
        if self.u16(opt) != 0x10b:
            raise PEError('PE_OPTIONAL_MAGIC: only PE32 is supported')
        self.entry_rva = self.u32(opt + 16)
        self.image_base = self.u32(opt + 28)
        self.image_size = self.u32(opt + 56)
        self.headers_size = self.u32(opt + 60)
        self.section_alignment = self.u32(opt + 32)
        self.file_alignment = self.u32(opt + 36)
        if not 0 < self.image_size <= MAX_IMAGE_SIZE or self.image_base + self.image_size > 1 << 32:
            raise PEError('PE_IMAGE_RANGE: invalid size or overflowing guest image')
        if self.entry_rva >= self.image_size:
            raise PEError('PE_ENTRY_RANGE: entrypoint outside image')
        table = opt + optional_size
        if not table + count * 40 <= self.headers_size <= min(len(data), self.image_size):
            raise PEError('PE_HEADERS_SIZE: section table or headers outside image')
        directory_count = self.u32(opt + 92)
        if directory_count > (optional_size - 96) // 8 or directory_count > 32:
            raise PEError('PE_DIRECTORY_COUNT: directories exceed optional header')
        self.directories = []
        for i in range(directory_count):
            value, size = self.u32(opt + 96 + i * 8), self.u32(opt + 100 + i * 8)
            self.directories.append({'index': i, 'address': value, 'size': size,
                                     'address_kind': 'file_offset' if i == 4 else 'rva'})
        self.sections = []
        virtual_spans, raw_spans = [], []
        for i in range(count):
            off = table + i * 40
            raw_name = self.span(off, 8).split(b'\0', 1)[0]
            # Escape unknown bytes in JSON rather than changing binary parsing.
            name = raw_name.decode('ascii', errors='backslashreplace')
            virtual_size, rva, raw_size, raw_offset = [self.u32(off + n) for n in (8, 12, 16, 20)]
            flags = self.u32(off + 36)
            extent = max(virtual_size, raw_size)
            if rva > self.image_size or (extent and (rva < self.headers_size or extent > self.image_size - rva)):
                raise PEError('PE_SECTION_RANGE: section outside image or intersects headers')
            if extent:
                virtual_spans.append((rva, rva + extent))
                if layout == 'mapped' and rva + extent > len(data):
                    raise PEError('PE_MAPPED_TRUNCATED: mapped section bytes are unavailable')
            if raw_size and layout == 'file':
                if raw_offset < self.headers_size:
                    raise PEError('PE_RAW_RANGE: section data intersects headers')
                self.span(raw_offset, raw_size)
                raw_spans.append((raw_offset, raw_offset + raw_size))
            self.sections.append({'name': name, 'rva': rva, 'address': self.image_base + rva,
                                  'virtual_size': virtual_size, 'raw_size': raw_size,
                                  'raw_offset': raw_offset, 'mapped_extent': extent,
                                  'characteristics': flags, 'executable': bool(flags & 0x20000000),
                                  'contains_code': bool(flags & 0x20),
                                  'readable': bool(flags & 0x40000000), 'writable': bool(flags & 0x80000000)})
        for spans in (virtual_spans, raw_spans):
            spans.sort()
            if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
                raise PEError('PE_SECTION_OVERLAP: ambiguous section mapping')

    def span(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset > len(self.data) - size:
            raise PEError(f'PE_BOUNDS: offset=0x{offset:x}, size=0x{size:x}')
        return self.data[offset:offset + size]

    def u16(self, offset: int) -> int:
        return struct.unpack('<H', self.span(offset, 2))[0]

    def u32(self, offset: int) -> int:
        return struct.unpack('<I', self.span(offset, 4))[0]

    def rva_bytes(self, rva: int, size: int) -> bytes:
        if type(rva) is not int or type(size) is not int or rva < 0 or size < 0 or rva > self.image_size - size:
            raise PEError('PE_RVA_RANGE: read outside image')
        if self.layout == 'mapped':
            return self.span(rva, size)
        if rva < self.headers_size and size <= self.headers_size - rva:
            return self.span(rva, size)
        for section in self.sections:
            relative = rva - section['rva']
            if 0 <= relative < section['mapped_extent']:
                if size > section['raw_size'] - relative:
                    raise PEError('PE_RVA_UNBACKED: requested bytes are not stored in file layout')
                return self.span(section['raw_offset'] + relative, size)
        raise PEError('PE_RVA_UNMAPPED: no section contains this RVA')

    def report(self) -> dict:
        entry_sections = [s['name'] for s in self.sections if s['rva'] <= self.entry_rva < s['rva'] + s['mapped_extent']]
        return {'schema_version': 1, 'format': 'PE32', 'layout': self.layout,
                'machine': f'0x{self.machine:04x}', 'powerpc_be_machine': self.machine == 0x1f2,
                'image_base': self.image_base, 'image_size': self.image_size,
                'available_size': len(self.data),
                'headers_size': self.headers_size, 'entry_rva': self.entry_rva,
                'entry_address': self.image_base + self.entry_rva, 'entry_sections': entry_sections,
                'section_alignment': self.section_alignment, 'file_alignment': self.file_alignment,
                'sections': self.sections, 'data_directories': self.directories,
                'diagnostics': ([{'code': 'PE_IMAGE_TAIL_UNAVAILABLE',
                                  'message': 'All section bytes exist, but the buffer is shorter than PE SizeOfImage. No missing bytes were synthesized.'}]
                                if self.layout == 'mapped' and len(self.data) < self.image_size else []),
                'analysis_status': {'exports': 'not_implemented', 'functions': 'not_implemented',
                                    'signature_verification': 'not_implemented',
                                    'instruction_decoding': 'separate_raw_ppc_inventory'}}


def resolve_xex_imports(image: PEImage, xex_report: dict) -> dict:
    """Read descriptors from original decoded memory, before import patching.

    Xenia xex_module.cc, SetupLibraryImports: BE32 high byte type, low16 ordinal.
    Type 0 is a value slot, type 1 a thunk. Neither proves a resolved native import.
    """
    if not isinstance(xex_report, dict) or not isinstance(xex_report.get('imports'), list):
        raise PEError('PE_IMPORT_SCHEMA: expected XEX report imports list')
    security = xex_report.get('security')
    if not isinstance(security, dict) or security.get('load_address') != image.image_base:
        raise PEError('PE_IMPORT_BASE: XEX and PE load addresses differ')
    libraries, diagnostics, total = [], [], 0
    for library in xex_report['imports']:
        if not isinstance(library, dict) or not isinstance(library.get('name'), str) or not isinstance(library.get('record_addresses'), list):
            raise PEError('PE_IMPORT_SCHEMA: invalid library')
        total += len(library['record_addresses'])
        if total > MAX_IMPORT_RECORDS:
            raise PEError('PE_IMPORT_LIMIT: too many records')
        records, previous = [], None
        for va in library['record_addresses']:
            if type(va) is not int or not 0 <= va < 1 << 32 or va % 4:
                raise PEError('PE_IMPORT_ADDRESS: expected aligned 32-bit address')
            value = int.from_bytes(image.rva_bytes(va - image.image_base, 4), 'big')
            kind, ordinal = value >> 24, value & 65535
            record = {'address': va, 'type': kind, 'ordinal': ordinal,
                      'kind': {0: 'value_slot', 1: 'thunk'}.get(kind, 'unknown'),
                      'native_resolution': 'not_implemented'}
            if kind == 0:
                previous = record
            elif kind == 1:
                if previous is not None and previous['ordinal'] == ordinal:
                    record['paired_value_address'] = previous['address']
                    previous['thunk_address'] = va
                else:
                    diagnostics.append({'code': 'XEX_IMPORT_THUNK_UNPAIRED', 'library': library['name'], 'address': va})
            else:
                diagnostics.append({'code': 'XEX_IMPORT_UNKNOWN_TYPE', 'library': library['name'], 'address': va, 'type': kind})
                previous = None
            records.append(record)
        libraries.append({'name': library['name'], 'record_count': len(records), 'records': records})
    return {'libraries': libraries, 'record_count': total, 'diagnostics': diagnostics,
            'status': ('descriptor_analysis_incomplete' if diagnostics
                       else 'descriptors_read_native_services_unresolved')}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--layout', choices=('file', 'mapped'), required=True)
    parser.add_argument('--xex-report', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.output:
            for source in (args.image, args.xex_report):
                if source and (source.resolve() == args.output.resolve() or
                               (source.exists() and args.output.exists() and source.samefile(args.output))):
                    raise PEError('PE_OUTPUT_COLLISION: report must not overwrite input')
        with args.image.open('rb') as stream:
            image = PEImage(stream.read(MAX_IMAGE_SIZE + 1), args.layout)
        report = image.report()
        if args.xex_report:
            # Metadata JSON only; bound it too instead of accepting unbounded input.
            with args.xex_report.open('rb') as stream:
                raw = stream.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise PEError('PE_IMPORT_REPORT_LIMIT: metadata exceeds 16 MiB')
            report['xex_imports'] = resolve_xex_imports(image, json.loads(raw))
        text = json.dumps(report, indent=2) + '\n'
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding='utf-8')
        else:
            print(text, end='')
        return 0
    except (OSError, PEError, json.JSONDecodeError, UnicodeDecodeError) as error:
        print(json.dumps({'code': 'PE_ANALYSIS_ERROR', 'message': str(error)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
