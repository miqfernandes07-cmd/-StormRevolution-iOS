#!/usr/bin/env python3
"""Bounded candidate entry ranges from direct-call omissions; no execution or patches."""
import argparse
import bisect
import importlib.util
import json
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('entry_pe',ROOT/'tools/xex_analysis/pe.py')
PE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(PE)


class RecoveryError(ValueError):pass


def executable(image, address):
    return next((s for s in image.sections if s['executable'] and s['address']<=address<s['address']+s['mapped_extent']),None)


def pdata_ranges(image):
    section=next((s for s in image.sections if s['name']=='.pdata'),None)
    if section is None:return []
    if image.machine!=0x1f2:raise RecoveryError('ENTRY_PDATA_MACHINE: Xbox PowerPC PE required')
    size=section['virtual_size']
    if size%8 or size>800000:raise RecoveryError('ENTRY_PDATA_SIZE: expected bounded 8-byte entries')
    raw=image.rva_bytes(section['rva'],size);ranges=[]
    for begin,packed in struct.iter_unpack('>II',raw):
        length=((packed>>8)&0x3fffff)*4;code=executable(image,begin)
        if begin%4 or not length or code is None or begin+length>code['address']+code['mapped_extent']:
            raise RecoveryError('ENTRY_PDATA_RANGE: malformed runtime function range')
        # ThirtyTwoBit is stored metadata, not evidence of MSR.SF or guest mode.
        ranges.append((begin,begin+length))
    return sorted(ranges)


def recover(image,entry,end,max_words=4096):
    if image.machine!=0x1f2 or type(entry) is not int or type(end) is not int or type(max_words) is not int:
        raise RecoveryError('ENTRY_MACHINE_OR_TYPE')
    code=executable(image,entry)
    if type(entry) is not int or type(end) is not int or entry%4 or end%4 or code is None or not entry<end<=code['address']+code['mapped_extent'] or not 1<=max_words<=4096:
        raise RecoveryError('ENTRY_RANGE: aligned executable bounds and 1..4096 words required')
    end=min(end,entry+max_words*4);queue=[entry];seen=set();outgoing=set();terminals=0;reason=None
    while queue and reason is None:
        pc=queue.pop()
        if pc in seen:continue
        if not entry<=pc<end:reason='ENTRY_BOUNDS';break
        seen.add(pc);word=int.from_bytes(image.rva_bytes(pc-image.image_base,4),'big');opcode=word>>26
        if word==0:reason='ENTRY_INVALID_WORD';break
        if word==0x4e800020:terminals+=1;continue
        if opcode in (16,18):
            width=16 if opcode==16 else 26;raw=word&(0xfffc if opcode==16 else 0x3fffffc)
            displacement=raw-(1<<width) if raw&(1<<(width-1)) else raw
            target=(displacement if word&2 else pc+displacement)&0xffffffff
            if executable(image,target) is None:reason='ENTRY_NONEXEC_TARGET';break
            if word&1:outgoing.add(target);queue.append(pc+4);continue
            if entry<=target<end:queue.append(target)
            else:outgoing.add(target);terminals+=1
            if opcode==16:queue.append(pc+4)
            continue
        if opcode in (2,3,17):reason='ENTRY_TRAP_OR_SYSCALL';break
        if opcode==19 and (word>>1&1023) in (16,528):
            bo=(word>>21)&30
            if (word>>1&1023)==16 and not word&1 and bo in (4,12,18,20):
                terminals+=1
                if bo!=20:queue.append(pc+4)
                continue
            reason='ENTRY_INDIRECT_OR_CONDITIONAL_RETURN';break
        if opcode==31 and (word>>1&1023) in (146,178):reason='ENTRY_CPU_MODE_WRITE';break
        queue.append(pc+4)
    size=max(seen)-entry+4 if seen else 0
    padding_nops=0
    if reason is None:
        if not terminals:reason='ENTRY_NO_TERMINAL'
        elif len(seen)*4!=size:
            gaps=[pc for pc in range(entry,entry+size,4) if pc not in seen]
            if all(int.from_bytes(image.rva_bytes(pc-image.image_base,4),'big')==0x60000000 for pc in gaps):padding_nops=len(gaps)
            else:reason='ENTRY_NONCONTIGUOUS'
    return {'address':entry,'size':size,'candidate':reason is None,'diagnostic':reason,
            'visited_words':len(seen),'padding_nops':padding_nops,'terminal_paths':terminals,'outgoing_targets':sorted(outgoing),
            'scope':'bounded_contiguous_direct_CFG_candidate_only','game_execution_approved':False}


def analyse(image,audit):
    if not isinstance(audit,dict) or not isinstance(audit.get('blocked_sites'),list):raise RecoveryError('ENTRY_AUDIT_SCHEMA')
    if len(audit['blocked_sites'])>100000:raise RecoveryError('ENTRY_AUDIT_SITE_LIMIT')
    targets={}
    for site in audit['blocked_sites']:
        if not isinstance(site,dict):raise RecoveryError('ENTRY_AUDIT_SCHEMA')
        if site.get('token')!='XENON_UNRESOLVED_STATIC_CALL':continue
        address=site.get('target')
        if type(address) is not int or not 0<=address<1<<32:raise RecoveryError('ENTRY_AUDIT_TARGET')
        targets[address]=targets.get(address,0)+1
    if len(targets)>10000:raise RecoveryError('ENTRY_TARGET_LIMIT')
    ranges=pdata_ranges(image);starts=[begin for begin,end in ranges];results=[]
    for address,calls in sorted(targets.items()):
        containing=[end for begin,end in ranges if begin<=address<end]
        section=executable(image,address)
        if section is None:raise RecoveryError('ENTRY_TARGET_NOT_EXECUTABLE')
        index=bisect.bisect_right(starts,address)
        end=min(containing) if containing else (starts[index] if index<len(starts) else section['address']+section['mapped_extent'])
        end=min(end,section['address']+section['mapped_extent'])
        result=recover(image,address,end);result['omitted_calls']=calls;results.append(result)
    return {'schema_version':1,'pdata_ranges':len(ranges),'unique_targets':len(targets),
            'candidates':results,'game_execution_approved':False,
            'requires_review':'Validate alternate entry ABI and emitted-code diagnostics before adding private config entries.'}


def private(path):
    resolved=path.resolve()
    if not resolved.is_relative_to((ROOT/'private').resolve()):raise RecoveryError('ENTRY_PRIVATE_PATH_REQUIRED')
    return resolved


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('image',type=Path);p.add_argument('--layout',choices=('file','mapped'),required=True);p.add_argument('--audit',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    try:
        image_path,audit_path,out=[private(x) for x in (args.image,args.audit,args.output)]
        if out.exists():raise RecoveryError('ENTRY_OUTPUT_EXISTS')
        if image_path.stat().st_size>PE.MAX_IMAGE_SIZE or audit_path.stat().st_size>16*1024*1024:raise RecoveryError('ENTRY_INPUT_SIZE_LIMIT')
        with image_path.open('rb') as stream: image_data=stream.read(PE.MAX_IMAGE_SIZE+1)
        with audit_path.open('rb') as stream: audit_data=stream.read(16*1024*1024+1)
        if len(image_data)>PE.MAX_IMAGE_SIZE or len(audit_data)>16*1024*1024:raise RecoveryError('ENTRY_INPUT_SIZE_LIMIT')
        image=PE.PEImage(image_data,args.layout);report=analyse(image,json.loads(audit_data))
        out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
        print(json.dumps({'unique_targets':report['unique_targets'],'candidate_ranges':sum(x['candidate'] for x in report['candidates']),'game_execution_approved':False}))
    except (ValueError,OSError) as error:print(str(error),file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
