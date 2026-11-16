#!/usr/bin/env python3
"""Compile selected unmodified SDK sources for iPhone; never load a title."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCES = (
    "src/base/clock_posix.cpp",
    "src/base/fiber_posix.cpp",
    "src/base/memory_posix.cpp",
    "src/base/threading_posix.cpp",
    "src/base/process_resources_posix.cpp",
)


def capture(command, *, cwd=None, timeout=120):
    result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout)
    return result.returncode, result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--experimental-ios-patch", action="store_true",
                        help="Apply the pinned VM-region adapter before compiling")
    args = parser.parse_args()
    source, output = args.sdk_source.resolve(), args.output.resolve()
    if output == source or source in output.parents:
        parser.error("Output must be outside the upstream source tree")
    reference = json.loads((ROOT / "config/rexglue_reference.json").read_text())
    code, revision = capture(["git", "rev-parse", "HEAD"], cwd=source)
    if code or revision.strip() != reference["commit"]:
        parser.error("SDK source revision does not match the pinned release")
    code, changes = capture(["git", "status", "--porcelain", "--untracked-files=no"], cwd=source)
    if code or changes.strip():
        parser.error("SDK source must be unmodified for this baseline probe")
    patch_digest = None
    if args.experimental_ios_patch:
        patch = reference["ios_experimental_patch"]
        patch_path = ROOT / patch["path"]
        patch_digest = hashlib.sha256(patch_path.read_bytes()).hexdigest()
        if patch_digest != patch["sha256"]:
            parser.error("Experimental patch digest mismatch")
        for item in patch["files"]:
            if hashlib.sha256((source / item["path"]).read_bytes()).hexdigest() != item["before_sha256"]:
                parser.error("SDK source file digest mismatch: " + item["path"])
        for command in (["git", "apply", "--check", str(patch_path)],
                        ["git", "apply", str(patch_path)]):
            code, log = capture(command, cwd=source)
            if code:
                parser.error("Experimental patch failed: " + log)
        for item in patch["files"]:
            if hashlib.sha256((source / item["path"]).read_bytes()).hexdigest() != item["after_sha256"]:
                parser.error("Patched source file digest mismatch: " + item["path"])
    compiler_code, compiler = capture(["xcrun", "--sdk", "iphoneos", "--find", "clang++"])
    sdk_code, sysroot = capture(["xcrun", "--sdk", "iphoneos", "--show-sdk-path"])
    if compiler_code or sdk_code:
        parser.error("An Apple iPhoneOS SDK and compiler are required")
    output.mkdir(parents=True, exist_ok=True)
    _, version = capture([compiler.strip(), "--version"])
    report = {"scope": "selected_unmodified_sdk_sources_compile_only",
              "sdk_commit": reference["commit"], "compiler": version,
              "target": "arm64-apple-ios17.0", "sources": [],
              "linked": False, "device_executed": False, "game_executed": False,
              "ios_runtime_qualified": False}
    if patch_digest:
        report["scope"] = "selected_patched_sdk_sources_compile_only"
        report["patch_sha256"] = patch_digest
    flags = [compiler.strip(), "-target", report["target"], "-isysroot", sysroot.strip(),
             "-std=c++23", "-fexperimental-library", "-DREX_BUILDING_BASE",
             "-DSPDLOG_COMPILED_LIB", "-fno-char8_t", "-fno-strict-aliasing",
             "-ffp-model=strict"]
    for directory in (source / "include", source / "src", source / "thirdparty/spdlog/include"):
        flags.extend(["-I", str(directory)])
    for name in SOURCES:
        stem = Path(name).stem
        command = flags + ["-c", str(source / name), "-o", str(output / (stem + ".o"))]
        try:
            code, log = capture(command)
        except subprocess.TimeoutExpired:
            code, log = 124, "Compiler exceeded the 120 second source budget\n"
        (output / (stem + ".txt")).write_text(log)
        report["sources"].append({"source": name, "returncode": code})
        print(f"{name}: {'compiled' if code == 0 else 'FAILED'}", flush=True)
    report["all_selected_sources_compiled"] = all(item["returncode"] == 0 for item in report["sources"])
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["all_selected_sources_compiled"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
