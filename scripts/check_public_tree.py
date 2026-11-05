"""Fail CI if known commercial/credential artifact types have been tracked.
Not a copyright scanner; manual review is still necessary for generated code.
"""
from pathlib import PurePosixPath
import subprocess
import sys

paths = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
forbidden_suffixes = {'.xex', '.iso', '.apk', '.ipa', '.p12', '.mobileprovision', '.xma', '.xwb', '.xsb'}
violations = [s for s in paths if s and (PurePosixPath(s).parts[0] in {'private', 'build', 'third_party'}
              or PurePosixPath(s).suffix.lower() in forbidden_suffixes)]
if violations:
    print('Forbidden tracked paths:', *violations, sep='\n', file=sys.stderr)
    sys.exit(1)
print('Tracked path hygiene passed (not a content/license audit).')
