#!/usr/bin/env bash
# Platform asset preparation; the original generated artwork is kept unchanged.
set -euo pipefail
source_image=${1:?icon artwork required}
catalog=${2:?output asset catalog required}
mkdir -p "$catalog/AppIcon.appiconset"
cat > "$catalog/Contents.json" <<'JSON'
{"info":{"author":"StormRevolution-iOS","version":1}}
JSON
cat > "$catalog/AppIcon.appiconset/Contents.json" <<'JSON'
{"images":[{"filename":"Icon.png","idiom":"universal","platform":"ios","size":"1024x1024"}],"info":{"author":"StormRevolution-iOS","version":1}}
JSON
/usr/bin/sips --resampleHeightWidth 1024 1024 "$source_image" --out "$catalog/AppIcon.appiconset/Icon.png" >/dev/null
python3 - "$catalog/AppIcon.appiconset/Icon.png" <<'PY'
import pathlib,struct,sys
data=pathlib.Path(sys.argv[1]).read_bytes()
assert data[:8]==b'\x89PNG\r\n\x1a\n'
assert struct.unpack_from('>II',data,16)==(1024,1024)
assert data[25]==2, 'The app icon must be opaque RGB'
print('Prepared opaque 1024x1024 iPhone app icon')
PY
