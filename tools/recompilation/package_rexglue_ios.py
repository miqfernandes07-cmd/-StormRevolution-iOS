#!/usr/bin/env python3
"""Package the pinned open source iPhone runtime; never include a game image."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def run(*args):
    return subprocess.check_output([str(x) for x in args], text=True)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_ios(path):
    info = run("xcrun", "vtool", "-show-build", path)
    if "platform IOS\n" not in info or "arm64" not in run("file", "-b", path):
        raise ValueError("Expected an iPhone ARM64 Mach-O: " + str(path))


def install_id(path):
    return run("xcrun", "otool", "-D", path).splitlines()[-1].strip()


def dependencies(path):
    return [line.strip().split(" (", 1)[0]
            for line in run("xcrun", "otool", "-L", path).splitlines()[1:] if line.strip()]


def rpaths(path):
    return re.findall(r"cmd LC_RPATH\s+cmdsize \d+\s+path (.*?) \(offset",
                      run("xcrun", "otool", "-l", path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-source", required=True, type=Path)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--moltenvk-archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source, build, output = args.sdk_source.resolve(), args.build.resolve(), args.output.resolve()
    if source == output or source in output.parents or output.exists():
        parser.error("Use a new output directory outside the SDK source tree")
    reference = json.loads((ROOT / "config/rexglue_reference.json").read_text())
    if run("git", "-C", source, "rev-parse", "HEAD").strip() != reference["commit"]:
        parser.error("SDK revision mismatch")
    for patch in reference["ios_experimental_patches"]:
        if digest(ROOT / patch["path"]) != patch["sha256"]:
            parser.error("Patch digest mismatch")
        for item in patch["files"]:
            if digest(source / item["path"]) != item["after_sha256"]:
                parser.error("Patched SDK source digest mismatch: " + item["path"])
    moltenvk = reference["moltenvk_ios"]
    if (args.moltenvk_archive.stat().st_size != moltenvk["archive_size"] or
            digest(args.moltenvk_archive) != moltenvk["archive_sha256"]):
        parser.error("MoltenVK archive does not match the official pinned asset")

    manifest = json.loads((build / "storm-ios-artifacts-Release.json").read_text())
    package = output / "runtime"
    frameworks, headers = package / "Frameworks", package / "include"
    frameworks.mkdir(parents=True)
    headers.mkdir()
    entries, aliases = [], {}
    for item in manifest["frameworks"]:
        name, path = item["name"], Path(item["path"]).resolve(strict=True)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ValueError("Invalid framework name")
        if not (path.is_relative_to(source) or path.is_relative_to(build)):
            raise ValueError("SDK binary is outside the verified build")
        check_ios(path)
        folder = frameworks / (name + ".framework")
        folder.mkdir()
        destination = folder / name
        shutil.copy2(path, destination)
        identity = f"@rpath/{name}.framework/{name}"
        aliases[path.name] = identity
        aliases[Path(install_id(path)).name] = identity
        entries.append((name, destination, identity, digest(path)))

    # Extract only the expected framework files and public headers; no tar paths are trusted.
    with tarfile.open(args.moltenvk_archive) as archive:
        prefix = moltenvk["framework_member"] + "/"
        for member in archive.getmembers():
            target = None
            if member.name.startswith(prefix):
                relative = Path(member.name[len(prefix):])
                if ".." in relative.parts or relative.is_absolute():
                    raise ValueError("Unsafe MoltenVK member")
                target = frameworks / "MoltenVK.framework" / relative
            elif member.name.startswith("MoltenVK/MoltenVK/include/"):
                relative = Path(member.name.removeprefix("MoltenVK/MoltenVK/include/"))
                if ".." in relative.parts or relative.is_absolute():
                    raise ValueError("Unsafe MoltenVK header")
                target = headers / relative
            if target is not None and member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as stream, target.open("wb") as dest:
                    shutil.copyfileobj(stream, dest)
    provider = frameworks / "MoltenVK.framework" / "MoltenVK"
    check_ios(provider)
    identity = "@rpath/MoltenVK.framework/MoltenVK"
    aliases[Path(install_id(provider)).name] = identity
    entries.append(("MoltenVK", provider, identity, digest(provider)))

    records = []
    for name, binary, identity, original_digest in entries:
        # These are unsigned build artifacts; the application installer signs every framework.
        subprocess.run(["codesign", "--remove-signature", str(binary)], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        run("xcrun", "install_name_tool", "-id", identity, binary)
        for dependency in dependencies(binary):
            replacement = aliases.get(Path(dependency).name)
            if replacement and replacement != dependency:
                run("xcrun", "install_name_tool", "-change", dependency, replacement, binary)
        for old in rpaths(binary):
            run("xcrun", "install_name_tool", "-delete_rpath", old, binary)
        run("xcrun", "install_name_tool", "-add_rpath", "@loader_path/..", binary)
        for dependency in dependencies(binary):
            if (dependency not in aliases.values() and
                    not dependency.startswith(("/usr/lib/", "/System/Library/"))):
                raise ValueError("Unpackaged framework dependency: " + dependency)
        check_ios(binary)
        binary.chmod(0o755)
        if name != "MoltenVK":
            (binary.parent / "Info.plist").write_bytes(plistlib.dumps({
                "CFBundleExecutable": name, "CFBundleName": name,
                "CFBundleIdentifier": "org.stormrevolution.runtime." + name,
                "CFBundleInfoDictionaryVersion": "6.0", "CFBundlePackageType": "FMWK",
                "CFBundleVersion": "1", "CFBundleShortVersionString": reference["release"].lstrip("v"),
                "CFBundleSupportedPlatforms": ["iPhoneOS"], "MinimumOSVersion": "17.0",
            }))
        records.append({"name": name, "original_sha256": original_digest,
                        "framework_sha256": digest(binary), "dependencies": dependencies(binary)})
        print("Packaged iOS framework:", name, flush=True)

    shutil.copytree(source / "include/rex", headers / "rex", dirs_exist_ok=True)
    shutil.copytree(build / "include/rex", headers / "rex", dirs_exist_ok=True)
    for relative, name in [("thirdparty/simde/simde", "simde"),
                           ("thirdparty/spdlog/include/spdlog", "spdlog"),
                           ("thirdparty/tomlplusplus/include/toml++", "toml++"),
                           ("thirdparty/sdl3/include/SDL3", "SDL3")]:
        shutil.copytree(source / relative, headers / name, dirs_exist_ok=True)
    for path in (source / "thirdparty/imgui").glob("*.h"):
        shutil.copy2(path, headers / path.name)
    shutil.copy2(ROOT / "out/vma/vk_mem_alloc.h", headers / "vk_mem_alloc.h")
    (package / "lib").mkdir()
    xenos = Path(manifest["xenos_archive"]).resolve(strict=True)
    if not (xenos.is_relative_to(source) or xenos.is_relative_to(build)):
        raise ValueError("Xenos archive is outside the verified build")
    if run("xcrun", "lipo", "-archs", xenos).strip() != "arm64":
        raise ValueError("Xenos archive is not ARM64")
    shutil.copy2(xenos, package / "lib/librexxenos.a")
    licenses = package / "licenses"
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if (path.is_file() and ".git" not in relative.parts and relative.parts[0] != "out" and
                path.name.lower().startswith(("license", "copying", "notice"))):
            destination = licenses / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
    (licenses / "MoltenVK").mkdir(parents=True, exist_ok=True)
    with tarfile.open(args.moltenvk_archive) as archive:
        with archive.extractfile("MoltenVK/LICENSE") as stream:
            (licenses / "MoltenVK/LICENSE").write_bytes(stream.read())

    report = {"scope": "open_source_runtime_frameworks_only", "sdk_commit": reference["commit"],
              "physical_offset_in_code": manifest["physical_offset_in_code"],
              "patches": reference["ios_experimental_patches"], "frameworks": records,
              "signed": False, "application_linked": False, "device_executed": False,
              "game_executed": False, "ios_runtime_qualified": False}
    (package / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    archive_path = output / "StormRuntime-iPhone-EXPERIMENTAL.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in package.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(package))
    # Include the actual open SDK source, with submodules and applied adapters, for rebuilding.
    def source_filter(info):
        parts = Path(info.name).parts
        return None if ".git" in parts or (len(parts) > 1 and parts[1] == "out") else info
    with tarfile.open(output / "ReXGlue-iPhone-source.tar.gz", "w:gz") as archive:
        archive.add(source, arcname="rexglue-source", filter=source_filter)
    shutil.copy2(args.moltenvk_archive, output / "MoltenVK-ios-original.tar")
    (output / "SHA256SUMS.txt").write_text("".join(
        digest(path) + "  " + path.name + "\n" for path in sorted(output.iterdir()) if path.is_file()))
    print("Packaged runtime contains no title, XEX or commercial AOT sources.")


if __name__ == "__main__":
    main()
