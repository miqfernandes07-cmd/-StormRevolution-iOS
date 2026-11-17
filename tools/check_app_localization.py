#!/usr/bin/env python3
"""Validate complete UI translations and format-string compatibility."""
import json,pathlib,re
root=pathlib.Path(__file__).resolve().parents[1]
s=(root/'ios/Localization/StormTranslations.inc').read_text()
v=json.loads(s[s.index('R"storm(')+8:s.rindex(')storm"')])
formats=lambda s: sorted(re.findall(r'%(?:@|[a-zA-Z])',s))
for key,entry in v.items():
    assert set(entry)=={'en','es','fr','de','it','ja'},key
    for language,value in entry.items():
        assert value and formats(value)==formats(key),(key,language)
for p in [*root.glob('ios/Native/*.mm'),root/'ios/Controls/StormControls.mm',root/'ios/Import/StormGameImporter.mm']:
    for key in re.findall(r'SL\(@"((?:[^"\\]|\\.)*)"\)',p.read_text()):
        assert json.loads('"'+key+'"') in v,(p,key)
print(f'{len(v)} app strings: 7 languages, complete translations and matching placeholders')
