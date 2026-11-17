#!/usr/bin/env python3
"""Replace only an ABI-checked renderer framework in an already linked private IPA."""
import argparse,copy,hashlib,json,pathlib,plistlib,struct,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
FRAMEWORK='Frameworks/rexgpu-xenos-vulkan.framework/'
BINARY=FRAMEWORK+'rexgpu-xenos-vulkan'
APP='Payload/StormNative.app/'
def sha(data):return hashlib.sha256(data).hexdigest()
def exports(data):
 magic,cpu,_,_,n,_,_,_=struct.unpack_from('<8I',data);assert magic==0xfeedfacf and cpu==0x100000c
 at=32;result=set()
 for _ in range(n):
  cmd,size=struct.unpack_from('<II',data,at);assert size>=8
  if cmd==2:
   so,count,st,ss=struct.unpack_from('<4I',data,at+8)
   for i in range(count):
    si,t,se,desc,value=struct.unpack_from('<IBBHQ',data,so+i*16)
    if si and t&1 and not t&0x10 and t&0xe==0xe and not desc&0x80:
     result.add(data[st+si:data.index(0,st+si)].decode())
  at+=size
 assert result,'No exported ABI symbols'
 return result

def refresh(base_ipa,baseline_sdk,new_sdk,output,source_run):
 expected=json.loads((ROOT/'config/rexglue_reference.json').read_text())
 with zipfile.ZipFile(base_ipa) as app,zipfile.ZipFile(baseline_sdk) as old,zipfile.ZipFile(new_sdk) as new:
  om=json.loads(old.read('manifest.json'));nm=json.loads(new.read('manifest.json'))
  assert nm['sdk_commit']==om['sdk_commit']==expected['commit']
  assert nm['physical_offset_in_code']==om['physical_offset_in_code']==1
  assert nm['patches']==expected['ios_experimental_patches']
  assert om['patches']==expected['ios_experimental_patches'][:-1]
  old_headers={n:sha(old.read(n)) for n in old.namelist() if n.startswith('include/') and not n.endswith('/')}
  new_headers={n:sha(new.read(n)) for n in new.namelist() if n.startswith('include/') and not n.endswith('/')}
  assert old_headers and old_headers==new_headers,'Public SDK headers changed; recompile the application instead'
  replacement=new.read(BINARY);assert b'Native GPU timing:' in replacement
  missing=exports(old.read(BINARY))-exports(replacement)
  assert not missing,('Renderer removed ABI symbols',sorted(missing))
  info=plistlib.loads(app.read(APP+'Info.plist'))
  assert info['CFBundleIdentifier']=='org.stormrevolution.native'
  assert info['CFBundleVersion']=='7' and info['CFBundleShortVersionString']=='0.6.0'
  for flag in ['UIFileSharingEnabled','LSSupportsOpeningDocumentsInPlace','GCSupportsGameMode','LSSupportsGameMode']:assert info[flag] is True
  info.update(CFBundleVersion='8',CFBundleShortVersionString='0.6.1')
  output.mkdir(parents=True,exist_ok=False);ipa=output/base_ipa.name
  replacement_names=[n for n in new.namelist() if n.startswith(FRAMEWORK) and not n.endswith('/')]
  assert replacement_names and BINARY in replacement_names
  with zipfile.ZipFile(ipa,'w',zipfile.ZIP_DEFLATED) as dst:
   for entry in app.infolist():
    if entry.filename.startswith(APP+FRAMEWORK):continue
    data=plistlib.dumps(info) if entry.filename==APP+'Info.plist' else app.read(entry)
    dst.writestr(copy.copy(entry),data)
   for name in replacement_names:
    entry=copy.copy(new.getinfo(name));entry.filename=APP+name
    dst.writestr(entry,new.read(name))
  with zipfile.ZipFile(ipa) as dst:
   changed=[];unchanged=0
   for name in set(app.namelist())|set(dst.namelist()):
    if name in app.namelist() and name in dst.namelist() and sha(app.read(name))==sha(dst.read(name)):unchanged+=1
    else:
     assert name==APP+'Info.plist' or name.startswith(APP+FRAMEWORK),name
     changed.append(name)
   assert dst.read(APP+'StormNative')==app.read(APP+'StormNative')
   assert dst.read(APP+'Assets.car')==app.read(APP+'Assets.car')
   assert b'Optional debugger thread naming disabled for native stability' in dst.read(APP+'StormNative')
  report=dict(scope='private_renderer_only_refresh',runtime_run=str(source_run),sdk_commit=nm['sdk_commit'],sdk_patches=nm['patches'],public_headers_identical=len(old_headers),exported_abi_preserved=True,main_executable_unchanged=True,icons_unchanged=True,other_frameworks_unchanged=True,unchanged_payload_entries=unchanged,changed_entries=sorted(changed),renderer_sha256=sha(replacement),source_ipa_sha256=sha(base_ipa.read_bytes()),device_executed=False,fps_gain_verified=False)
 (output/'runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 (output/'SHA256SUMS.txt').write_text(sha(ipa.read_bytes())+'  '+ipa.name+'\n')
 (output/'validation.json').write_text(json.dumps(dict(scope='private_native_renderer_refresh',iphone_arm64_linked=True,contains_recompiled_title=True,contains_game_assets=False,signed=False,device_executed=False,gameplay_verified=False),indent=2)+'\n')
 print('Renderer refreshed:',len(old_headers),'identical public headers;',unchanged,'unchanged payload entries')
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['base-ipa','baseline-sdk','new-sdk','output']:p.add_argument('--'+name,type=pathlib.Path,required=True)
 p.add_argument('--source-run',required=True);a=p.parse_args();refresh(a.base_ipa,a.baseline_sdk,a.new_sdk,a.output,a.source_run)
