#!/usr/bin/env python3
"""Compile selected unmodified SDK sources for iPhone; never load a title."""
import argparse
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
    flags = [compiler.strip(), "-target", report["target"], "-isysroot", sysroot.strip(),
             "-std=c++23", "-fexperimental-library", "-DREX_BUILDING_BASE",
             "-DSPDLOG_COMPILED_LIB", "-D_XOPEN_SOURCE=700"]
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
