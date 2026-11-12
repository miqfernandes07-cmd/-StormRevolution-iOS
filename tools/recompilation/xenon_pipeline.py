#!/usr/bin/env python3
"""Private, pinned XenonRecomp CLI adapter. Requires Python 3.11+.

Does not download tools, keys or game files. Plans are the default; --execute is
explicit. A reviewed config digest is required for the recompilation stage.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib

PINNED_COMMIT = "ddd128bcca99fe8bfbb99bea583c972351fa6ace"
ROOT = Path(__file__).resolve().parents[2]


class PipelineError(ValueError):
    pass


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def private_path(path: Path, private: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(private.resolve()) or resolved == private.resolve():
        raise PipelineError(f"PRIVATE_PATH_REQUIRED: {path}")
    return resolved


def validate_patch_series(manifest: dict, checkout: Path) -> dict:
    """An explicit experimental series; never authorize arbitrary dirty sources."""
    config = ROOT / 'config/xenon_experimental_series.json'
    if manifest.get('source_patch_series_sha256') != digest(config):
        raise PipelineError('XENON_PATCH_SERIES_DIGEST_MISMATCH')
    series = json.loads(config.read_text(encoding='utf-8'))
    if (manifest.get('source_patch_series') != series.get('id')
            or series.get('base_commit') != PINNED_COMMIT
            or series.get('game_execution_approved') is not False):
        raise PipelineError('XENON_PATCH_SERIES_ID_OR_POLICY')
    for patch in series['patches']:
        path = (ROOT / patch['path']).resolve()
        if not path.is_relative_to(ROOT.resolve()) or digest(path) != patch['sha256']:
            raise PipelineError('XENON_PATCH_CONTENT_CHANGED')
    changes = subprocess.run(['git', '-C', str(checkout), 'diff', '--name-only', 'HEAD', '--'],
                             text=True, capture_output=True, check=False)
    if changes.returncode or set(changes.stdout.splitlines()) != set(series['files']):
        raise PipelineError('XENON_PATCH_UNEXPECTED_TRACKED_CHANGES')
    for name, expected in series['files'].items():
        path = (checkout / name).resolve()
        if not path.is_relative_to(checkout.resolve()) or digest(path) != expected:
            raise PipelineError('XENON_PATCH_SOURCE_CHANGED')
    return series


def toolchain(manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest,dict) or not isinstance(manifest.get("source_checkout"),str):
        raise PipelineError("XENON_MANIFEST_SCHEMA: object and source_checkout string required")
    if manifest.get("source_commit") != PINNED_COMMIT:
        raise PipelineError("XENON_SOURCE_PIN_MISMATCH")
    checkout = Path(manifest["source_checkout"]).resolve()
    result = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=False)
    if result.returncode or result.stdout.strip() != PINNED_COMMIT:
        raise PipelineError("XENON_CHECKOUT_PIN_MISMATCH")
    series = None
    if 'source_patch_series' in manifest:
        series = validate_patch_series(manifest, checkout)
    else:
        if 'source_patch_series_sha256' in manifest:
            raise PipelineError('XENON_PATCH_SERIES_ID_REQUIRED')
        clean = subprocess.run(["git", "-C", str(checkout), "diff", "--quiet", "HEAD", "--"],
                               capture_output=True, check=False)
        if clean.returncode:
            raise PipelineError("XENON_CHECKOUT_TRACKED_CHANGES")
    result = {}
    for name in ("analyse", "recomp", "context"):
        record = manifest.get(name)
        if (not isinstance(record,dict) or not isinstance(record.get("path"),str)
                or not isinstance(record.get("sha256"),str)):
            raise PipelineError(f"XENON_MANIFEST_SCHEMA:{name}")
        path = Path(record["path"]).resolve()
        if not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) or digest(path) != record["sha256"]:
            raise PipelineError(f"XENON_TOOL_DIGEST_MISMATCH:{name}")
        result[name] = path
    result["source_commit"] = PINNED_COMMIT
    if series is not None:
        if digest(result['context']) != series['context_sha256']:
            raise PipelineError('XENON_PATCH_CONTEXT_CHANGED')
        result['source_patch_series'] = series['id']
        result['game_execution_approved'] = False
    return result


def plan_analyse(tools: dict, xex: Path, output: Path, private: Path) -> dict:
    xex = private_path(xex, private)
    output = private_path(output, private)
    if not xex.is_file():
        raise PipelineError("XEX_INPUT_MISSING")
    if output == xex:
        raise PipelineError("OUTPUT_OVERWRITES_INPUT")
    return {"stage": "analyse", "command": [str(tools["analyse"]), str(xex), str(output)],
            "output": str(output), "input": str(xex), "input_sha256": digest(xex), "source_commit": PINNED_COMMIT,
            "source_patch_series": tools.get("source_patch_series"), "game_execution_approved": False}


def plan_recompile(tools: dict, config: Path, reviewed_digest: str, private: Path) -> dict:
    config = private_path(config, private)
    if digest(config) != reviewed_digest:
        raise PipelineError("REVIEWED_CONFIG_DIGEST_REQUIRED_OR_CHANGED")
    data = tomllib.loads(config.read_text(encoding="utf-8"))
    main = data.get("main", {})
    if not isinstance(main,dict):
        raise PipelineError("CONFIG_MAIN_TABLE_REQUIRED")
    required = ("file_path", "out_directory_path", "switch_table_file_path")
    if any(not isinstance(main.get(key), str) or not main[key] for key in required):
        raise PipelineError("CONFIG_REQUIRED_MAIN_PATH_MISSING")
    # No title updates until their patched executable identity is explicitly handled.
    if main.get("patch_file_path") or main.get("patched_file_path"):
        raise PipelineError("TITLE_UPDATE_PIPELINE_NOT_IMPLEMENTED")
    paths = {key: private_path(config.parent / main[key], private) for key in required}
    for key in ("file_path", "switch_table_file_path"):
        if not paths[key].is_file():
            raise PipelineError(f"CONFIG_INPUT_MISSING:{key}")
    output = paths["out_directory_path"]
    for source in (config,paths["file_path"],paths["switch_table_file_path"]):
        if source.is_relative_to(output):
            raise PipelineError("OUTPUT_MUST_NOT_CONTAIN_INPUTS")
    return {"stage": "recompile", "command": [str(tools["recomp"]), str(config), str(tools["context"])],
            "output": str(output), "config_sha256": reviewed_digest,
            "input": str(paths["file_path"]), "input_sha256": digest(paths["file_path"]), "source_commit": PINNED_COMMIT,
            "status": "requires_generated_code_and_diagnostics_review",
            "source_patch_series": tools.get("source_patch_series"), "game_execution_approved": False}


def validate_identity(plan: dict, private: Path) -> None:
    spec = importlib.util.spec_from_file_location("storm_xex",ROOT/"tools/xex_analysis/xex.py")
    xex = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(xex)
    path = private_path(Path(plan["input"]),private)
    with path.open("rb") as stream:
        data = stream.read(xex.MAX_FILE_SIZE + 1)
    try:
        report = xex.inspect(data)
        reference = json.loads((ROOT/"config/game_reference.json").read_text(encoding="utf-8"))
        result = xex.validate(report,reference)
    except ValueError as error:
        raise PipelineError(f"XEX_IDENTITY_VALIDATION_FAILED:{error}") from error
    if not result["matches_reference"]:
        raise PipelineError("XEX_IDENTITY_MISMATCH: title/version/region/size/hash must match reference")
    if report["sha256"] != plan["input_sha256"]:
        raise PipelineError("XEX_CHANGED_AFTER_PLAN")
    if plan["stage"] == "recompile" and digest(Path(plan["command"][1])) != plan["config_sha256"]:
        raise PipelineError("CONFIG_CHANGED_AFTER_REVIEW")


def audit_generated(output: Path) -> dict:
    """Conservative emitted-source gate, not a C++ parser or reachability proof."""
    root = output.resolve()
    literals = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)
    unsafe = re.compile(r'\b(__builtin_debugtrap|__builtin_trap|__builtin_unreachable)\s*\(')
    files, sites, indirect, total = 0, [], 0, 0
    for path in sorted(output.rglob('*.cpp')):
        if not path.resolve().is_relative_to(root):
            raise PipelineError('XENON_GENERATED_SOURCE_ESCAPE')
        with path.open('rb') as stream:
            data = stream.read(16 * 1024 * 1024 + 1)
        total += len(data)
        if len(data) > 16 * 1024 * 1024 or total > 512 * 1024 * 1024:
            raise PipelineError('XENON_GENERATED_AUDIT_SIZE_LIMIT')
        source = data.decode('utf-8')
        newlines = [index for index, char in enumerate(source) if char == '\n']
        code = literals.sub(lambda match: ''.join('\n' if c == '\n' else ' ' for c in match[0]), source)
        for match in unsafe.finditer(code):
            sites.append({'file': path.relative_to(output).as_posix(),
                          'line': bisect.bisect_right(newlines, match.start()) + 1, 'token': match[1]})
        # The upstream emitter uses a comment instead of a call when a direct
        # target has no symbol. Treat that exact marker as omitted behavior.
        for match in re.finditer(r'(?m)^[ \t]*//[ \t]*ERROR\b(?:[ \t]+(?:0x)?([0-9A-Fa-f]+))?', source):
            sites.append({'file': path.relative_to(output).as_posix(),
                          'line': bisect.bisect_right(newlines, match.start()) + 1,
                          'token': 'XENON_UNRESOLVED_STATIC_CALL',
                          'target': int(match[1], 16) if match[1] else None})
        # A .long emitted for an undecodable word, including zero, is not
        # evidence of a harmless NOP. Padding must be excluded by reviewed ranges.
        for match in re.finditer(r'(?m)^[ \t]*//[ \t]*\.long[ \t]+([^\n]*)', source):
            sites.append({'file': path.relative_to(output).as_posix(),
                          'line': bisect.bisect_right(newlines, match.start()) + 1,
                          'token': 'XENON_UNDECODED_WORD'})
        indirect += len(re.findall(r'\bPPC_CALL_INDIRECT_FUNC\s*\(', code))
        files += 1
    return {'cpp_files': files, 'blocked_sites': sites, 'indirect_call_sites': indirect,
            'game_execution_approved': False, 'scope': 'emitted_cpp_lexical_gate_only'}


def execute(plan: dict, log_path: Path, private: Path) -> int:
    log_path = private_path(log_path, private)
    output = Path(plan["output"])
    if log_path == output:
        raise PipelineError("LOG_MUST_DIFFER_FROM_OUTPUT")
    # Never run upstream on unverified commercial identity or modified config.
    # Plans are useful with synthetic inputs; execution is title-specific.
    validate_identity(plan,private)
    # Never overwrite artifacts from a previous analysis or recompilation.
    if output.exists():
        raise PipelineError("OUTPUT_ALREADY_EXISTS")
    if log_path.exists():
        raise PipelineError("LOG_ALREADY_EXISTS")
    output.parent.mkdir(parents=True, exist_ok=True)
    if plan["stage"] == "recompile":
        output.mkdir()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("xb") as log:
        result = subprocess.run(plan["command"], stdout=log, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise PipelineError(f"XENON_TOOL_FAILED:{result.returncode}; inspect private log")
    log = log_path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"\b(error|fatal|warning|unsupported|unimplemented)\b|not implemented|unrecognized instruction|unable to decode instruction|has RC bit enabled but no comparison|unexpected .* instruction|ends prematurely", log, re.I):
        raise PipelineError("XENON_DIAGNOSTICS_REQUIRE_REVIEW; inspect private log")
    if plan["stage"] == "analyse" and not output.is_file():
        raise PipelineError("XENON_ANALYSIS_OUTPUT_MISSING")
    if plan["stage"] == "recompile":
        audit = audit_generated(output)
        audit_path = private_path(log_path.with_suffix(log_path.suffix + '.audit.json'), private)
        with audit_path.open('x', encoding='utf-8') as stream:
            json.dump(audit, stream, indent=2)
            stream.write('\n')
        if not audit['cpp_files']:
            raise PipelineError("XENON_GENERATED_CPP_MISSING")
        if audit['blocked_sites']:
            raise PipelineError('XENON_GENERATED_CODE_REQUIRES_REVIEW: trap/unreachable/omitted-call sites; inspect private audit')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--log", type=Path)
    commands = parser.add_subparsers(dest="stage", required=True)
    analyse = commands.add_parser("analyse")
    analyse.add_argument("xex", type=Path)
    analyse.add_argument("output", type=Path)
    recomp = commands.add_parser("recompile")
    recomp.add_argument("config", type=Path)
    recomp.add_argument("--reviewed-config-sha256", required=True)
    args = parser.parse_args()
    try:
        private = ROOT / "private"
        manifest = private_path(args.manifest, private)
        tools = toolchain(manifest)
        plan = (plan_analyse(tools,args.xex,args.output,private) if args.stage == "analyse"
                else plan_recompile(tools,args.config,args.reviewed_config_sha256,private))
        if args.execute:
            if not args.log:
                raise PipelineError("PRIVATE_LOG_REQUIRED")
            execute(plan,args.log,private)
        plan["executed"] = args.execute
        print(json.dumps(plan,indent=2))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({"code":"XENON_PIPELINE_ERROR","message":str(error)}),file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
