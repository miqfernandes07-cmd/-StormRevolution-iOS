#!/usr/bin/env python3
"""Explicit private host diagnostic of reviewed generated entry functions, never title boot."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
NAME=re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')
FUNCTION=re.compile(r'^PPC_FUNC_IMPL\(__imp__(\w+)\) \{\n.*?^\}',re.M|re.S)
HANDLERS={'__imp__RtlImageXexHeaderField','__imp__NtAllocateVirtualMemory','__imp__NtFreeVirtualMemory'}


class ProbeError(ValueError):pass


def sha(data):return hashlib.sha256(data).hexdigest()


def private(path):
    path=Path(path).resolve()
    if not path.is_relative_to((ROOT/'private').resolve()) or path==ROOT/'private':raise ProbeError('PREFIX_PRIVATE_PATH_REQUIRED')
    return path


def bounded(path,limit):
    with Path(path).open('rb') as stream:data=stream.read(limit+1)
    if len(data)>limit:raise ProbeError('PREFIX_INPUT_SIZE_LIMIT')
    return data


def extract(generated,names):
    if not isinstance(names,list) or not 1<=len(names)<=32 or any(not isinstance(n,str) or not NAME.fullmatch(n) for n in names) or len(set(names))!=len(names):
        raise ProbeError('PREFIX_FUNCTION_LIST')
    functions={};total=0
    for path in sorted(generated.glob('*.cpp')):
        if not path.resolve().is_relative_to(generated.resolve()):raise ProbeError('PREFIX_SOURCE_ESCAPE')
        source=bounded(path,16*1024*1024);total+=len(source)
        if total>512*1024*1024:raise ProbeError('PREFIX_SOURCE_SIZE_LIMIT')
        for match in FUNCTION.finditer(source.decode('utf-8')):
            if match[1] not in names:continue
            if match[1] in functions:raise ProbeError('PREFIX_DUPLICATE_FUNCTION')
            body=match[0]
            # This bounded experiment supports checked scalar access only.
            if re.search(r'__builtin_(?:debugtrap|trap|unreachable)|//\s*(?:ERROR|\.long)|\bbase\s*\+|simde_mm_(?:load|store)|__sync_|__atomic_',body):
                raise ProbeError('PREFIX_UNQUALIFIED_SELECTED_FUNCTION:'+match[1])
            functions[match[1]]=body
    if set(functions)!=set(names):raise ProbeError('PREFIX_SELECTED_FUNCTION_MISSING')
    return functions


def verify_context(generated,upstream):
    # The pinned CLI prepends this exact include preamble when copying context.
    if generated!=b'#pragma once\n#include "ppc_config.h"\n\n'+upstream:
        raise ProbeError('PREFIX_CONTEXT_ABI_MISMATCH')


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def checked_config(path,digest):
    data=bounded(private(path),1024*1024)
    if sha(data)!=digest:raise ProbeError('PREFIX_REVIEWED_CONFIG_DIGEST_REQUIRED')
    c=json.loads(data)
    if not isinstance(c,dict):raise ProbeError('PREFIX_CONFIG_OBJECT_REQUIRED')
    if any(not isinstance(c.get(key),dict) for key in ('function_sha256','header_sha256','module_layout')):raise ProbeError('PREFIX_CONFIG_TABLES_REQUIRED')
    return c


def prepare(c):
    generated=private(c['generated']);image=private(c['image']);xex=private(c['xex']);manifest=private(c['toolchain_manifest'])
    pipeline=module('prefix_pipeline',ROOT/'tools/recompilation/xenon_pipeline.py');tools=pipeline.toolchain(manifest)
    image_data=bounded(image,256*1024*1024);xex_data=bounded(xex,256*1024*1024)
    if sha(image_data)!=c['image_sha256'] or sha(xex_data)!=c['xex_sha256']:raise ProbeError('PREFIX_INPUT_DIGEST_CHANGED')
    xe=module('prefix_xex',ROOT/'tools/xex_analysis/xex.py');identity=xe.inspect(xex_data)
    if not xe.validate(identity,json.loads((ROOT/'config/game_reference.json').read_text()))['matches_reference']:raise ProbeError('PREFIX_XEX_IDENTITY')
    pe=module('prefix_pe',ROOT/'tools/xex_analysis/pe.py');loaded=pe.PEImage(image_data,'mapped')
    if loaded.image_base!=identity['security']['load_address'] or loaded.image_base+loaded.entry_rva!=identity['entry_point']:raise ProbeError('PREFIX_IMAGE_ENTRY_MISMATCH')
    functions=extract(generated,c['functions']);mapping_data=bounded(generated/'ppc_func_mapping.cpp',16*1024*1024)
    if sha(mapping_data)!=c['mapping_sha256']:raise ProbeError('PREFIX_FUNCTION_MAPPING_CHANGED')
    mappings={n:int(a,16) for a,n in re.findall(rb'\{\s*(0x[0-9a-fA-F]+),\s*(\w+)\s*\}',mapping_data)}
    mappings={n.decode():a for n,a in mappings.items()}
    if c['entry_name'] not in functions or mappings.get(c['entry_name'])!=identity['entry_point']:raise ProbeError('PREFIX_ENTRY_SYMBOL_MISMATCH')
    if any(n not in mappings for n in functions):raise ProbeError('PREFIX_FUNCTION_MAPPING_MISSING')
    for name,body in functions.items():
        if sha(body.encode())!=c['function_sha256'].get(name):raise ProbeError('PREFIX_FUNCTION_CHANGED:'+name)
    for name in ('ppc_config.h','ppc_context.h','ppc_recomp_shared.h'):
        data=bounded(private(generated/name),16*1024*1024)
        if sha(data)!=c['header_sha256'].get(name):raise ProbeError('PREFIX_HEADER_CHANGED:'+name)
        if name=='ppc_context.h':verify_context(data,bounded(tools['context'],16*1024*1024))
    imports=pe.resolve_xex_imports(loaded,identity)
    slot=c['handle_slot'];record=next((r for lib in imports['libraries'] if lib['name']=='xboxkrnl.exe' for r in lib['records'] if r['address']==slot and r['kind']=='value_slot' and r['ordinal']==0x193 and 'thunk_address' not in r),None)
    if record is None:raise ProbeError('PREFIX_HANDLE_IMPORT_NOT_DATA_SLOT')
    word=int.from_bytes(loaded.rva_bytes(slot-loaded.image_base,4),'big')
    stack_base,stack_size=c['stack_base'],c['stack_size']
    for value in (stack_base,stack_size,*c['module_layout'].values()):
        if type(value) is not int or not 0<value<1<<32:raise ProbeError('PREFIX_LAYOUT_TYPE_OR_RANGE')
    if stack_base%16 or stack_size%16 or not 4096<=stack_size<=16*1024*1024 or stack_base+stack_size>1<<32:raise ProbeError('PREFIX_STACK_RANGE')
    calls={n for body in functions.values() for n in re.findall(r'\b(\w+)\(ctx, base\);',body)}
    missing=sorted(calls-set(functions)-HANDLERS)
    if len(missing)>2048:raise ProbeError('PREFIX_GUARD_COUNT_LIMIT')
    guards='\n'.join('PPC_FUNC('+n+'){throw std::runtime_error("UNIMPLEMENTED_NATIVE_CALLEE: '+n+'");}' for n in missing)
    bodies='\n'.join(body+'\nPPC_FUNC('+n+'){++entered;std::printf("AOT_ENTER '+n+'\\n");__imp__'+n+'(ctx,base);}' for n,body in functions.items())
    template=(ROOT/'tools/recompilation/prefix_probe_main.cpp.in').read_text()
    values={'GUARDS':guards,'FUNCTIONS':bodies,'REGISTRATIONS':'\n'.join('    table.add('+str(mappings[n])+'u,'+n+');' for n in functions),
            'IMAGE_SIZE':len(image_data),'IMAGE_BASE':loaded.image_base,'ENTRY_ADDRESS':identity['entry_point'],
            'HEADER_SIZE':identity['payload_offset'],'STACK_BASE':stack_base,'STACK_SIZE':stack_size,
            'MODULE_VARIABLE':c['module_layout']['variable'],'MODULE_DESCRIPTOR':c['module_layout']['descriptor'],'MODULE_HEADER':c['module_layout']['header'],
            'HANDLE_SLOT':slot,'HANDLE_WORD':word}
    template=re.sub(r'@(\w+)@',lambda m:str(values[m[1]])+'u' if type(values[m[1]]) is int else values[m[1]],template)
    return template,{'generated':str(generated),'image':str(image),'xex':str(xex),'selected_functions':len(functions),'callee_guards':len(missing),
                     'scope':'private_controlled_native_entry_prefix_diagnostic','entry_ABI_qualified':False,'full_aot_image_approved':False,'game_initializes':False,'gameplay':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--reviewed-config-sha256',required=True);p.add_argument('--clang',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--system-ubsan',action='store_true');a=p.parse_args()
    try:
        config=checked_config(a.config,a.reviewed_config_sha256);source,report=prepare(config);work=private(a.work)
        if work.exists():raise ProbeError('PREFIX_WORK_ALREADY_EXISTS')
        report.update(executed=False,config_sha256=a.reviewed_config_sha256)
        if a.execute:
            work.mkdir(parents=True);(work/'prefix.cpp').write_text(source)
            cmd=[str(a.clang.absolute()),'-std=c++20','-O1','-fwrapv','-fno-strict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(ROOT/'runtime'),'-I'+report['generated'],'-I'+str(Path(config['toolchain_manifest']).resolve().parent)]
            module('prefix_toolchain',ROOT/'tools/recompilation/xenon_pipeline.py').toolchain(private(config['toolchain_manifest']))
            checkout=json.loads(private(config['toolchain_manifest']).read_text())['source_checkout']
            cmd[-1]='-I'+str(Path(checkout)/'thirdparty/simde')
            cmd += [str(work/'prefix.cpp'),*[str(ROOT/'runtime'/x) for x in ('cpu/aot_dispatch.cpp','memory/address_space.cpp','kernel/executable_module.cpp','kernel/virtual_memory.cpp')],'-o',str(work/'prefix')]
            if a.system_ubsan:cmd+=['-fno-sanitize-link-runtime','-lubsan']
            build=subprocess.run(cmd,capture_output=True,text=True,timeout=120);(work/'build.log').write_text(build.stdout+build.stderr)
            if build.returncode:raise ProbeError('PREFIX_BUILD_FAILED: inspect private build.log')
            if sha(bounded(private(config['image']),256*1024*1024))!=config['image_sha256'] or sha(bounded(private(config['xex']),256*1024*1024))!=config['xex_sha256']:raise ProbeError('PREFIX_INPUT_CHANGED_BEFORE_RUN')
            result=subprocess.run([str(work/'prefix'),report['image'],report['xex']],capture_output=True,text=True,timeout=15);(work/'run.log').write_text(result.stdout+result.stderr)
            report.update(executed=True,returncode=result.returncode,stdout=result.stdout,entered_functions=len(re.findall(r'(?m)^AOT_ENTER ',result.stdout)),binary_sha256=sha((work/'prefix').read_bytes()))
            (work/'report.json').write_text(json.dumps(report,indent=2)+'\n')
            if result.returncode or 'PREFIX_STOP ' not in result.stdout:raise ProbeError('PREFIX_DIAGNOSTIC_FAILED: inspect private run.log')
        print(json.dumps(report,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError,subprocess.TimeoutExpired) as e:print(json.dumps({'code':'PREFIX_PROBE_ERROR','message':str(e)}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
