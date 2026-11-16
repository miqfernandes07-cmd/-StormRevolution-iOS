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
MAX_FUNCTIONS=64
NAME=re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')
FUNCTION=re.compile(r'^PPC_FUNC_IMPL\(__imp__(\w+)\) \{\n.*?^\}',re.M|re.S)
HANDLERS={'__imp__KeQuerySystemTime','__imp__KeTlsAlloc','__imp__KeTlsFree','__imp__KeTlsGetValue','__imp__KeTlsSetValue','__imp__XGetAVPack','__imp__XexCheckExecutablePrivilege','__imp__RtlEnterCriticalSection','__imp__RtlTryEnterCriticalSection','__imp__RtlLeaveCriticalSection','__imp__RtlImageXexHeaderField','__imp__NtAllocateVirtualMemory','__imp__NtFreeVirtualMemory','__imp__KeGetCurrentProcessType','__imp__KeSetCurrentProcessType','__imp__RtlInitializeCriticalSection','__imp__RtlInitializeCriticalSectionAndSpinCount'}


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
    if not isinstance(names,list) or not 1<=len(names)<=MAX_FUNCTIONS or any(not isinstance(n,str) or not NAME.fullmatch(n) for n in names) or len(set(names))!=len(names):
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


def video_profile(config):
    # Xenia documents only its virtual VGA response (6), explicitly as a stub.
    # Require an opt-in profile; do not infer an iOS cable or a working renderer.
    profile=config.get('diagnostic_video')
    if profile is None:return 0
    if (not isinstance(profile,dict) or set(profile)!={'kind','av_pack'}
            or profile['kind']!='virtual_vga' or type(profile['av_pack']) is not int
            or profile['av_pack']!=6):
        raise ProbeError('PREFIX_DIAGNOSTIC_VIDEO_PROFILE')
    return 6


def dynamic_tls_profile(config,identity,xex_data):
    tls=config.get('dynamic_tls')
    if (not isinstance(tls,dict) or set(tls)!={'address','slots'}
            or any(type(tls[k]) is not int for k in tls)
            or not 0<tls['address']<1<<32 or tls['address']%4
            or not 1<=tls['slots']<=2048 or tls['address']+tls['slots']*4>1<<32):
        raise ProbeError('PREFIX_DYNAMIC_TLS_LAYOUT')
    tls_header=next((h for h in identity['optional_headers'] if h['key']=='0x00020104'),None)
    expected_slots=1024
    if tls_header:
        offset=tls_header.get('offset')
        if type(offset) is not int or not 0<=offset<=len(xex_data)-16:
            raise ProbeError('PREFIX_TLS_HEADER_RANGE')
        expected_slots=int.from_bytes(xex_data[offset:offset+4],'big') or 1024
    if tls['slots']!=expected_slots:raise ProbeError('PREFIX_TLS_SLOT_COUNT_MISMATCH')
    return tls


def checked_config(path,digest):
    data=bounded(private(path),1024*1024)
    if sha(data)!=digest:raise ProbeError('PREFIX_REVIEWED_CONFIG_DIGEST_REQUIRED')
    c=json.loads(data)
    if not isinstance(c,dict):raise ProbeError('PREFIX_CONFIG_OBJECT_REQUIRED')
    if any(not isinstance(c.get(key),dict) for key in ('function_sha256','header_sha256','module_layout')):raise ProbeError('PREFIX_CONFIG_TABLES_REQUIRED')
    return c


def prepare(c):
    av_pack=video_profile(c)
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
    tls=dynamic_tls_profile(c,identity,xex_data)
    hardware=c['hardware_info']
    if not isinstance(hardware,dict) or any(type(hardware.get(k)) is not int for k in ('slot','address','flags','logical_cpus')):
        raise ProbeError('PREFIX_HARDWARE_LAYOUT')
    if not 0<=hardware['flags']<1<<32 or not 1<=hardware['logical_cpus']<=6:
        raise ProbeError('PREFIX_HARDWARE_PROFILE')
    hardware_record=next((r for lib in imports['libraries'] if lib['name']=='xboxkrnl.exe' for r in lib['records'] if r['address']==hardware['slot'] and r['kind']=='value_slot' and r['ordinal']==0x156 and 'thunk_address' not in r),None)
    if hardware_record is None:raise ProbeError('PREFIX_HARDWARE_IMPORT_NOT_DATA_SLOT')
    hardware_word=int.from_bytes(loaded.rva_bytes(hardware['slot']-loaded.image_base,4),'big')
    word=int.from_bytes(loaded.rva_bytes(slot-loaded.image_base,4),'big')
    stack_base,stack_size=c['stack_base'],c['stack_size']
    pib=c['process_block']
    thread=c['diagnostic_thread']
    if type(thread) is not int or not 0<thread<=0xfffffeb0 or thread%4:raise ProbeError('PREFIX_THREAD_IDENTITY')
    thread_identity=c['thread_identity']
    if (not isinstance(thread_identity,dict) or set(thread_identity)!={'pcr','id'}
            or any(type(thread_identity[k]) is not int for k in thread_identity)
            or not 0<thread_identity['pcr']<=0xfffffeac or thread_identity['pcr']%4
            or not 0<thread_identity['id']<1<<32):raise ProbeError('PREFIX_PCR_IDENTITY_LAYOUT')
    if type(pib) is not int or not 0<pib<=0xffffffa0 or pib%4:raise ProbeError('PREFIX_PROCESS_LAYOUT')
    for value in (stack_base,stack_size,*c['module_layout'].values()):
        if type(value) is not int or not 0<value<1<<32:raise ProbeError('PREFIX_LAYOUT_TYPE_OR_RANGE')
    if stack_base%16 or stack_size%16 or not 4096<=stack_size<=16*1024*1024 or stack_base+stack_size>1<<32:raise ProbeError('PREFIX_STACK_RANGE')
    calls={n for body in functions.values() for n in re.findall(r'\b(\w+)\(ctx, base\);',body)}
    missing=sorted(calls-set(functions)-HANDLERS)
    if len(missing)>2048:raise ProbeError('PREFIX_GUARD_COUNT_LIMIT')
    guards='\n'.join('PPC_FUNC('+n+'){throw std::runtime_error("UNIMPLEMENTED_NATIVE_CALLEE: '+n+'");}' for n in missing)
    bodies='\n'.join(body+'\nPPC_FUNC('+n+'){++entered;std::printf("AOT_ENTER '+n+'\\n");__imp__'+n+'(ctx,base);}' for n,body in functions.items())
    template=(ROOT/'tools/recompilation/prefix_probe_main.cpp.in').read_text()
    values={'TLS_ADDRESS':tls['address'],'TLS_SLOTS':tls['slots'],'DIAGNOSTIC_AV_PACK':av_pack,'GUARDS':guards,'FUNCTIONS':bodies,'REGISTRATIONS':'\n'.join('    table.add('+str(mappings[n])+'u,'+n+');' for n in functions),
            'IMAGE_SIZE':len(image_data),'IMAGE_BASE':loaded.image_base,'ENTRY_ADDRESS':identity['entry_point'],
            'HARDWARE_ADDRESS':hardware['address'],'HARDWARE_FLAGS':hardware['flags'],'HARDWARE_CPUS':hardware['logical_cpus'],'HARDWARE_SLOT':hardware['slot'],'HARDWARE_WORD':hardware_word,
            'PCR_ADDRESS':thread_identity['pcr'],'THREAD_NUMERIC_ID':thread_identity['id'],'DIAGNOSTIC_THREAD':thread,'PROCESS_BLOCK':pib,'HEADER_SIZE':identity['payload_offset'],'STACK_BASE':stack_base,'STACK_SIZE':stack_size,
            'MODULE_VARIABLE':c['module_layout']['variable'],'MODULE_DESCRIPTOR':c['module_layout']['descriptor'],'MODULE_HEADER':c['module_layout']['header'],
            'HANDLE_SLOT':slot,'HANDLE_WORD':word}
    template=re.sub(r'@(\w+)@',lambda m:str(values[m[1]])+'u' if type(values[m[1]]) is int else values[m[1]],template)
    return template,{'generated':str(generated),'image':str(image),'xex':str(xex),'selected_functions':len(functions),'callee_guards':len(missing),
                     'diagnostic_av_pack':av_pack or None,'video_rendering_implemented':False,'dynamic_tls_slots':tls['slots'],'static_tls_ABI_qualified':False,'thread_identity_fields_only':True,
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
            cmd += [str(work/'prefix.cpp'),*[str(ROOT/'runtime'/x) for x in ('cpu/aot_dispatch.cpp','memory/address_space.cpp','kernel/executable_module.cpp','kernel/virtual_memory.cpp','kernel/process_state.cpp','kernel/tls_state.cpp','kernel/imports.cpp')],'-o',str(work/'prefix')]
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
