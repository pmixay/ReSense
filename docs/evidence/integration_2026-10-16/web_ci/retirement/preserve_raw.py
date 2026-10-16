"""Preserve the web owner's raw evidence; capture never removes or rewrites source files.

check/restore use the ZIP and manifest only, independently of the original worktree.
Python 3.10+ standard library; invoke with -B to avoid generating worktree caches.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PREFIX = "docs/evidence/integration_2026-10-16/web_ci/"
RETIREMENT = PREFIX + "retirement/"
BRANCH_MANIFEST = "docs/evidence/integration_2026-10-16/branch_archive/manifest.json"
BRANCH = "integration/web-ci-20261016"
INTEGRATION = "integration/2026-10-15-16"
COUNT = 19
ZIP = "web-raw.zip"
SUPPORT = (".gitattributes", "README.md", "preserve_raw.py", "test_preserve_raw.py")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def git(*args):
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}, check=False,
    )
    require(result.returncode == 0, f"Git failed: {args!r}: {result.stderr.decode('utf-8', 'replace')}")
    return result.stdout


def names(*args):
    return sorted(p.decode("utf-8") for p in git("ls-files", "-z", *args).split(b"\0") if p)


def is_cache(path):
    parts = PurePosixPath(path).parts
    return bool(set(parts) & {"__pycache__", ".pytest_cache", ".ruff_cache"}) or path.endswith((".pyc", ".pyd", ".so"))


def safe_member(path):
    p = PurePosixPath(path)
    require(
        p.as_posix() == path and path.startswith(PREFIX) and not path.startswith(RETIREMENT)
        and not p.is_absolute() and ".." not in p.parts and "\\" not in path and ":" not in path,
        f"Invalid payload path: {path!r}",
    )
    return p


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=True) + "\n")


def validate(manifest, archive):
    require(manifest["schema"] == 1, "Unsupported manifest schema")
    records = manifest["files"]
    paths = [r["path"] for r in records]
    require(len(records) == COUNT and len(set(paths)) == COUNT, "Expected 19 unique files")
    recorded = {r["path"]: r for r in manifest["branch_archive"]["worktree_entry"]["status"]}
    require(set(paths) == set(recorded), "Payload paths differ from frozen branch inventory")
    for record in records:
        safe_member(record["path"])
        original = recorded[record["path"]]
        require(original["status"] == "!!" and original["kind"] == "file", "Unexpected recorded file kind/status")
        require(record["bytes"] == original["bytes"] and record["mtime_ns"] == original["mtime_ns"], "Recorded metadata drift")
        require(record["original_absolute_path"] == manifest["source_worktree"] + "/" + record["path"], "Original path mismatch")
    actual = identity(archive.read_bytes())
    require(actual == {k: manifest["archive"][k] for k in ("bytes", "sha256")}, "ZIP identity mismatch")
    with zipfile.ZipFile(archive) as zipped:
        members = zipped.infolist()
        require(sorted(z.filename for z in members) == sorted(paths), "ZIP membership mismatch")
        for member in members:
            require(not member.is_dir() and not stat.S_ISLNK(member.external_attr >> 16), "Non-file ZIP member")
            record = next(r for r in records if r["path"] == member.filename)
            require(identity(zipped.read(member)) == {k: record[k] for k in ("bytes", "sha256")}, "Raw file identity mismatch")
    return {"verified_files": COUNT, "raw_bytes": sum(r["bytes"] for r in records), "archive": actual}


def restore(manifest, archive, destination):
    result = validate(manifest, archive)  # Validate every member before creating the destination.
    require(destination.parent.is_dir() and not destination.exists(), "Restore destination must be new; parent must exist")
    destination.mkdir()
    with zipfile.ZipFile(archive) as zipped:
        for record in manifest["files"]:
            target = destination.joinpath(*safe_member(record["path"]).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(zipped.read(record["path"]))
            os.utime(target, ns=(record["mtime_ns"], record["mtime_ns"]))
            require(identity(target.read_bytes()) == {k: record[k] for k in ("bytes", "sha256")}, "Restored bytes mismatch")
    require(sorted(p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file())
            == sorted(r["path"] for r in manifest["files"]), "Restored file inventory mismatch")
    return {**result, "destination": destination.as_posix(), "reads_original_worktree": False}


def capture(branch_manifest_path, external):
    require(external.parent.is_dir() and not external.exists(), "External keeper must be new; parent must exist")
    require(git("branch", "--show-current").decode().strip() == BRANCH, "Wrong capture branch")
    source_head = git("rev-parse", "HEAD").decode().strip()
    integration_tip = git("rev-parse", INTEGRATION).decode().strip()
    branch_bytes = branch_manifest_path.read_bytes()
    require(branch_bytes == git("cat-file", "blob", f"{integration_tip}:{BRANCH_MANIFEST}"), "Branch inventory is not the committed integration copy")
    frozen = json.loads(branch_bytes)
    matches = [w for w in frozen["worktrees_before"] if Path(w["worktree"]).resolve() == ROOT]
    require(len(matches) == 1, "Source worktree absent/ambiguous in frozen inventory")
    entry = matches[0]
    require(entry["HEAD"] == source_head, "Source head advanced since branch inventory")
    expected = sorted(r["path"] for r in entry["status"])
    require(len(expected) == COUNT and len(set(expected)) == COUNT, "Frozen inventory must contain 19 unique paths")

    ignored = names("--others", "--ignored", "--exclude-standard")
    untracked = names("--others", "--exclude-standard")
    unknown = sorted(p for p in ignored + untracked if p not in expected and not p.startswith(RETIREMENT) and not is_cache(p))
    require(not unknown, f"Additional non-cache owner files require preservation: {unknown}")
    require(sorted(p for p in ignored if p.startswith(PREFIX) and not p.startswith(RETIREMENT)) == expected,
            "Live ignored raw inventory differs from frozen inventory")
    tracked = names("--cached")
    accounted = set(tracked + ignored + untracked)
    physical_extra = []
    for directory, dirs, files in os.walk(ROOT, followlinks=False):
        dirs[:] = [d for d in dirs if d != ".git"]
        for file in files:
            relative = (Path(directory) / file).relative_to(ROOT).as_posix()
            if relative != ".git" and relative not in accounted:
                physical_extra.append(relative)
    require(not physical_extra, f"Physical files outside Git inventory: {physical_extra}")

    payload, records = {}, []
    for original in sorted(entry["status"], key=lambda r: r["path"]):
        relative = original["path"]
        safe_member(relative)
        path = ROOT / relative
        info = path.stat()
        require(path.is_file() and not path.is_symlink(), f"Not a regular source file: {relative}")
        require(info.st_size == original["bytes"] and info.st_mtime_ns == original["mtime_ns"], f"Source metadata changed: {relative}")
        payload[relative] = path.read_bytes()
        records.append({"path": relative, "original_absolute_path": path.as_posix(),
                        **identity(payload[relative]), "mtime_ns": info.st_mtime_ns})

    tracked_evidence = []
    for relative in sorted(p for p in tracked if p.startswith(PREFIX)):
        old_blob = git("rev-parse", f"{source_head}:{relative}").decode().strip()
        require(old_blob == git("rev-parse", f"{integration_tip}:{relative}").decode().strip(), f"Tracked evidence not preserved in integration: {relative}")
        tracked_evidence.append({"path": relative, "git_blob": old_blob})

    archive = HERE / ZIP
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        for relative, data in payload.items():
            member = zipfile.ZipInfo(relative, date_time=(2026, 10, 16, 0, 0, 0))
            member.create_system = 3
            member.external_attr = (stat.S_IFREG | 0o644) << 16
            member.compress_type = zipfile.ZIP_DEFLATED
            zipped.writestr(member, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    manifest = {
        "schema": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_worktree": ROOT.as_posix(), "source_head": source_head, "source_branch": BRANCH,
        "branch_archive": {"manifest_path": branch_manifest_path.as_posix(),
                           "repository_path": BRANCH_MANIFEST, **identity(branch_bytes),
                           "integration_tip": integration_tip,
                           "manifest_git_blob": git("rev-parse", f"{integration_tip}:{BRANCH_MANIFEST}").decode().strip(),
                           "worktree_entry": entry},
        "archive": {"file": ZIP, **identity(archive.read_bytes()), "entries": COUNT, "compression": "deflate-9"},
        "files": records, "external_keeper": external.as_posix(),
        "inventory": {"ignored_files": ignored, "untracked_retirement_deliverables": untracked,
                      "additional_noncache_owner_files": unknown, "unaccounted_physical_files": physical_extra,
                      "cache_paths_retained_in_place": [p for p in ignored + untracked if is_cache(p)],
                      "tracked_evidence_preserved_in_integration": tracked_evidence},
        "storage_policy": "Every raw file is stored verbatim in ZIP; no tracked-text deduplication is used.",
    }
    write_json(HERE / "manifest.json", manifest)
    local = validate(manifest, archive)
    external.mkdir()
    shutil.copyfile(archive, external / ZIP)
    shutil.copyfile(HERE / "manifest.json", external / "manifest.json")
    require((external / ZIP).read_bytes() == archive.read_bytes(), "External ZIP copy differs")
    require((external / "manifest.json").read_bytes() == (HERE / "manifest.json").read_bytes(), "External manifest differs")
    roundtrip = restore(manifest, external / ZIP, external / "roundtrip-restored")
    for record in records:
        path = ROOT / record["path"]
        require(identity(path.read_bytes()) == {k: record[k] for k in ("bytes", "sha256")}, "Source changed during preservation")
        require(path.stat().st_mtime_ns == record["mtime_ns"], "Source mtime changed during preservation")
    require(names("--others", "--ignored", "--exclude-standard") == ignored, "Ignored inventory changed during capture")
    proof = {
        "schema": 1, "manifest": identity((HERE / "manifest.json").read_bytes()),
        "verification": local, "external_zip_and_manifest_identical": True,
        "branch_inventory_path_and_metadata_match_count": COUNT, "original_files_unchanged_count": COUNT,
        "roundtrip": roundtrip, "tracked_evidence_preserved_count": len(tracked_evidence),
        "additional_noncache_owner_files": unknown,
        "supporting_files": {name: identity((HERE / name).read_bytes()) for name in SUPPORT},
        "python": sys.version, "source_deletion_performed": False,
    }
    write_json(HERE / "verification.json", proof)
    for name in (*SUPPORT, "verification.json"):
        shutil.copyfile(HERE / name, external / name)
    return proof


def check(external=None, git_ref=None):
    manifest_bytes = (HERE / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    proof = json.loads((HERE / "verification.json").read_bytes())
    require(identity(manifest_bytes) == proof["manifest"], "Manifest differs from roundtrip proof")
    result = validate(manifest, HERE / ZIP)
    for name, expected in proof["supporting_files"].items():
        require(identity((HERE / name).read_bytes()) == expected, f"Supporting file differs: {name}")
    if external is not None:
        for name in (ZIP, "manifest.json", "verification.json", *SUPPORT):
            require((external / name).read_bytes() == (HERE / name).read_bytes(), f"External keeper differs: {name}")
    if git_ref:
        for name in (ZIP, "manifest.json", "verification.json", *SUPPORT):
            require(git("cat-file", "blob", f"{git_ref}:{RETIREMENT}{name}") == (HERE / name).read_bytes(), f"Committed bytes differ: {name}")
    return {**result, "external_copy_checked": external.as_posix() if external else None,
            "git_ref_checked": git_ref, "reads_original_worktree": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("capture")
    create.add_argument("--branch-manifest", type=Path, required=True)
    create.add_argument("--external", type=Path, required=True)
    verify = commands.add_parser("check")
    verify.add_argument("--external", type=Path)
    verify.add_argument("--git-ref")
    recover = commands.add_parser("restore")
    recover.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "capture":
        result = capture(args.branch_manifest.resolve(), args.external.resolve())
    elif args.command == "check":
        result = check(args.external.resolve() if args.external else None, args.git_ref)
    else:
        manifest = json.loads((HERE / "manifest.json").read_bytes())
        result = restore(manifest, HERE / ZIP, args.destination.resolve())
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
