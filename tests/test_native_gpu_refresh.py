"""Packaging/ABI guard checks with synthetic Mach-O modules; no game or SDK execution."""
import copy,hashlib,importlib.util,json,pathlib,plistlib,struct,tempfile,unittest,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('native_gpu_refresh',ROOT/'tools/recompilation/refresh_native_gpu.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def image(symbols,marker=b''):
    strings=b'\0';entries=b''
    for name in symbols:
        entries+=struct.pack('<IBBHQ',len(strings),15,1,0,0x1000)
        strings+=name.encode()+b'\0'
    return struct.pack('<8I',0xfeedfacf,0x100000c,0,6,1,24,0,0)+struct.pack('<6I',2,24,56,len(symbols),56+len(entries),len(strings))+entries+strings+marker
class NativeGPURefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='storm-synthetic-gpu-package-');self.root=pathlib.Path(self.temp.name)
        self.ref=json.loads((ROOT/'config/rexglue_reference.json').read_text())
        self.symbols=['_rex_gpu_init','_rex_frame_stats']
        self.old=image(self.symbols);self.new=image(self.symbols,b'Native GPU timing:')
        self.headers={'include/rex/config.h':b'unchanged-public-interface'}
        self.base=self.root/'base.ipa';self.baseline=self.root/'old.zip';self.sdk=self.root/'new.zip';self.output=self.root/'out'
        info=dict(CFBundleIdentifier='org.stormrevolution.native',CFBundleVersion='7',CFBundleShortVersionString='0.6.0',UIFileSharingEnabled=True,LSSupportsOpeningDocumentsInPlace=True,GCSupportsGameMode=True,LSSupportsGameMode=True)
        self.payload={m.APP+'Info.plist':plistlib.dumps(info),m.APP+'StormNative':b'SYNTHETIC-MAIN Optional debugger thread naming disabled for native stability',m.APP+'Assets.car':b'synthetic-icons',m.APP+'Frameworks/Other.framework/Other':b'unchanged-other-component',m.APP+m.BINARY:self.old}
        with zipfile.ZipFile(self.base,'w') as z:
            for n,v in self.payload.items():z.writestr(n,v)
        self.write_sdk(self.baseline,self.old,self.headers,self.ref['ios_experimental_patches'][:-1]);self.write_sdk(self.sdk,self.new,self.headers,self.ref['ios_experimental_patches'])
    def tearDown(self):self.temp.cleanup()
    def write_sdk(self,path,binary,headers,patches,digest=None):
        manifest=dict(sdk_commit=self.ref['commit'],physical_offset_in_code=1,patches=patches,frameworks=[dict(name='rexgpu-xenos-vulkan',framework_sha256=digest or hashlib.sha256(binary).hexdigest())])
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('manifest.json',json.dumps(manifest));z.writestr(m.BINARY,binary)
            for n,v in headers.items():z.writestr(n,v)
    def run_refresh(self):return m.refresh(self.base,self.baseline,self.sdk,self.output,'synthetic-only')
    def test_changes_only_renderer_and_version(self):
        report=self.run_refresh();self.assertTrue(report['main_executable_unchanged']);self.assertEqual(report['public_headers_identical'],1)
        with zipfile.ZipFile(self.output/self.base.name) as z:
            for name,value in self.payload.items():
                if name not in [m.APP+'Info.plist',m.APP+m.BINARY]:self.assertEqual(z.read(name),value)
            self.assertEqual(z.read(m.APP+m.BINARY),self.new)
            info=plistlib.loads(z.read(m.APP+'Info.plist'));self.assertEqual(info['CFBundleVersion'],'8');self.assertTrue(info['LSSupportsGameMode'])
    def test_changed_public_header_requires_recompile(self):
        self.write_sdk(self.sdk,self.new,{'include/rex/config.h':b'incompatible'},self.ref['ios_experimental_patches'])
        with self.assertRaisesRegex(AssertionError,'Public SDK headers changed'):self.run_refresh()
        self.assertFalse(self.output.exists())
    def test_missing_export_refuses_update(self):
        self.write_sdk(self.sdk,image(self.symbols[:1],b'Native GPU timing:'),self.headers,self.ref['ios_experimental_patches'])
        with self.assertRaisesRegex(AssertionError,'removed ABI symbols'):self.run_refresh()
        self.assertFalse(self.output.exists())
    def test_wrong_renderer_digest_refuses_update(self):
        self.write_sdk(self.sdk,self.new,self.headers,self.ref['ios_experimental_patches'],digest='0'*64)
        with self.assertRaisesRegex(AssertionError,'Renderer digest'):self.run_refresh()
        self.assertFalse(self.output.exists())
    def test_unpatched_sdk_refuses_update(self):
        self.write_sdk(self.sdk,self.new,self.headers,self.ref['ios_experimental_patches'][:-1])
        with self.assertRaises(AssertionError):self.run_refresh()
        self.assertFalse(self.output.exists())
if __name__=='__main__':unittest.main()
