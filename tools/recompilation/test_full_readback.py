#!/usr/bin/env python3
"""Exercise the actual patched SDK method with deterministic Vulkan/fence failures."""
import argparse,pathlib,subprocess,tempfile,os
root=pathlib.Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--sdk-source',type=pathlib.Path,required=True);p.add_argument('--cxx',default=os.environ.get('CXX','c++'));a=p.parse_args()
s=(a.sdk_source/'src/gpu/xenos/vulkan/command_processor.cpp').read_text()
profile=s[s.index('// Native readback diagnostics'):s.index('constexpr TBuiltInResource')]
implementation=s[s.index('bool VulkanCommandProcessor::IssueDrawMemexportReadbackFullPath('):s.index('\nbool VulkanCommandProcessor::IssueDrawMemexportReadbackFastPath(')]
start=s.index('  for (u32 i = 0; i < 2; ++i) {\n    if (memexport_full_readback_')
cleanup=s[start:s.index('  memexport_full_readback_ = {};',start)+len('  memexport_full_readback_ = {};')]
harness=(root/'tests/integration/rexglue_full_readback.cpp.in').read_text().replace('/*PROFILE*/',profile).replace('/*IMPLEMENTATION*/',implementation).replace('/*CLEANUP*/',cleanup)
with tempfile.TemporaryDirectory(prefix='storm-full-readback-') as t:
 t=pathlib.Path(t);(t/'check.cpp').write_text(harness)
 subprocess.run([a.cxx,'-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fno-sanitize-recover=undefined',str(t/'check.cpp'),'-o',str(t/'check')],check=True)
 subprocess.run([str(t/'check')],check=True)
