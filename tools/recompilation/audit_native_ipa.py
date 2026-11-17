#!/usr/bin/env python3
"""Inspect this port's IPA statically; never claim device execution or gameplay."""
import struct,zipfile,plistlib,json,hashlib,pathlib,sys
CPU_ARM64=0x100000C

def macho(data):
    magic=struct.unpack_from('>I',data)[0]
    if magic in (0xCAFEBABE,0xCAFEBABF):
        count=struct.unpack_from('>I',data,4)[0];stride=32 if magic==0xCAFEBABF else 20
        for i in range(count):
            pos=8+i*stride;cpu=struct.unpack_from('>I',data,pos)[0]
            if cpu==CPU_ARM64:
                offset,size=struct.unpack_from('>QQ' if stride==32 else '>II',data,pos+8);data=data[offset:offset+size];break
        else:raise ValueError('No ARM64 slice')
    magic,cpu,sub,kind,ncmds,sizeofcmds,flags,reserved=struct.unpack_from('<8I',data)
    assert magic==0xFEEDFACF and cpu==CPU_ARM64
    result={'kind':kind,'dependencies':[],'rpaths':[],'guest_code_bytes':0};pos=32
    for i in range(ncmds):
        cmd,size=struct.unpack_from('<II',data,pos);assert size>=8 and pos+size<=len(data)
        blob=data[pos:pos+size]
        if cmd==0x32:
            platform,minimum,sdk=struct.unpack_from('<III',blob,8)
            result['platform']=platform;result['minimum_ios']='.'.join(str(x) for x in (minimum>>16,(minimum>>8)&255,minimum&255))
        elif cmd in (0xC,0x80000018,0x8000001F):
            offset=struct.unpack_from('<I',blob,8)[0];result['dependencies'].append(blob[offset:].split(b'\0')[0].decode())
        elif cmd==0x8000001C:
            offset=struct.unpack_from('<I',blob,8)[0];result['rpaths'].append(blob[offset:].split(b'\0')[0].decode())
        elif cmd==0x19:
            sections=struct.unpack_from('<I',blob,64)[0]
            for section in range(sections):
                at=72+80*section;name=blob[at:at+16].split(b'\0')[0]
                if name==b'__rexguest':result['guest_code_bytes']+=struct.unpack_from('<Q',blob,at+40)[0]
        pos+=size
    assert result.get('platform')==2,result
    return result

def audit(path):
    with zipfile.ZipFile(path) as archive:
        names=set(archive.namelist());root='Payload/StormNative.app/'
        info=plistlib.loads(archive.read(root+'Info.plist'));assert info['CFBundleExecutable']=='StormNative'
        main=macho(archive.read(root+'StormNative'));assert main['kind']==2
        assert main['guest_code_bytes']>1024*1024
        assert '@executable_path/Frameworks' in main['rpaths'],main['rpaths']
        frameworks={}
        for entry in sorted(names):
            if entry.startswith(root+'Frameworks/') and entry.count('/')==4 and not entry.endswith('/'):
                folder,binary=entry.rsplit('/',2)[1:]
                if folder==binary+'.framework':frameworks[binary]=macho(archive.read(entry))
        assert len(frameworks)==17,len(frameworks)
        for image in [main]+list(frameworks.values()):
            for dependency in image['dependencies']:
                if dependency.startswith('@rpath/'):
                    assert root+'Frameworks/'+dependency.removeprefix('@rpath/') in names,dependency
                else:assert dependency.startswith(('/System/Library/','/usr/lib/')),dependency
        assert root+'ThirdPartyLicenses/LICENSE' in names
        assert not any(n.lower().endswith(('.cpk','.xex','.iso')) for n in names)
        return {'scope':'static_private_ipa_audit','size':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'bundle_identifier':info['CFBundleIdentifier'],'bundle_version':info['CFBundleVersion'],
                'architecture':'arm64','main':main,'frameworks':frameworks,
                'device_executed':False,'gameplay_verified':False}
if __name__=='__main__':
    path=pathlib.Path(sys.argv[1]);report=audit(path);path.with_suffix('.audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Static IPA audit passed:',report['size'],'bytes;',len(report['frameworks']),'iOS frameworks;',report['main']['guest_code_bytes'],'bytes of recompiled code')
