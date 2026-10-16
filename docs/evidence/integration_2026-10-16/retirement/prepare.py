"""Read-only Git inventory and lossless non-Git backups; NO retirement operation.

Run with python -B. Only new output files under the approved external directory
and (with --record) this preparation folder are written. No refs are updated.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EVIDENCE = HERE.parent
EXTERNAL = Path("C:/Users/alikh/AppData/Local/Temp/opencode/resense-retirement-20261016")
INTEGRATION = "refs/heads/integration/2026-10-15-16"
WEB = "refs/heads/integration/web-ci-20261016"
WEB_SHA = "f29e212abe933dcfa76ee9b0ea4afb9cd95bf810"
PR_HEAD = "b0c9c17cde65a59ddf93fb2799bc94a8a6a31bd1"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def run(*args, cwd=ROOT):
    return subprocess.run(args, cwd=cwd, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}).stdout


def git(*args, cwd=ROOT):
    return run("git", *args, cwd=cwd)


def decode(data):
    return data.decode("utf-8", "surrogateescape")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True)
        stream.write("\n")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archives(ref="HEAD"):
    branch = load_module("retired_archive", EVIDENCE / "branch_archive/archive.py")
    manifest, check = branch.check(ROOT)
    web = load_module("web_preserve", EVIDENCE / "web_ci/retirement/preserve_raw.py")
    web_check = web.check(git_ref=ref)
    # The sealed archive check alone checks filesystem bytes. Also prove those
    # exact files, including its checksum manifest, are present in the Git ref.
    folder = EVIDENCE / "branch_archive"
    for name in (*branch.EVIDENCE_FILES, "file_manifest.json"):
        path = folder / name
        require(git("cat-file", "blob", f"{ref}:{path.relative_to(ROOT).as_posix()}")
                == path.read_bytes(), f"Archive not identical in {ref}: {name}")
    return manifest, {"branch": check, "web": web_check}


def refs():
    local = {}
    for line in decode(git("for-each-ref", "--format=%(refname)%09%(objectname)",
                           "refs/heads", "refs/remotes/origin")).splitlines():
        name, value = line.split("\t")
        local[name] = value
    remote = {}
    for line in decode(git("ls-remote", "--heads", "origin")).splitlines():
        value, name = line.split("\t")
        remote[name] = value
    return local, remote


def worktrees():
    result, item = [], {}
    for token in git("worktree", "list", "--porcelain", "-z").split(b"\0"):
        if not token:
            if item:
                result.append(item)
                item = {}
            continue
        key, _, value = decode(token).partition(" ")
        item[key] = value or True
    if item:
        result.append(item)
    return result


def status(path):
    tokens = iter(git("status", "--porcelain=v1", "-z", "--untracked-files=all",
                      "--ignored=traditional", cwd=path).split(b"\0"))
    entries = []
    for token in tokens:
        if not token:
            continue
        text = decode(token)
        entry = {"status": text[:2], "path": text[3:]}
        if "R" in text[:2] or "C" in text[:2]:
            entry["original_path"] = decode(next(tokens))
        entries.append(entry)
    return entries


def non_git(path):
    """Physical walk, not just ignore rules; never follow links/reparse points.

    Unknown special files, nested Git metadata and submodules block backup. All
    directories (including empty ones) are recorded, all non-index files hashed.
    """
    tracked = {decode(p) for p in git("ls-files", "--cached", "-z", cwd=path).split(b"\0") if p}
    records, directories = [], []

    def walk(directory):
        for child in sorted(directory.iterdir()):
            relative = child.relative_to(path).as_posix()
            if relative == ".git":
                continue
            info = child.lstat()
            require(not child.is_symlink() and not (getattr(info, "st_file_attributes", 0) & 0x400),
                    f"KEEP: symlink/reparse point requires separate preservation: {child}")
            require(child.name != ".git", f"KEEP: nested Git repository: {child}")
            if stat.S_ISDIR(info.st_mode):
                require(relative not in tracked, f"KEEP: submodule: {child}")
                directories.append(relative)
                walk(child)
            else:
                require(stat.S_ISREG(info.st_mode), f"KEEP: special file: {child}")
                if relative not in tracked:
                    records.append({"path": relative, "bytes": info.st_size,
                                    "mtime_ns": info.st_mtime_ns, "mode": info.st_mode,
                                    "sha256": sha(child)})
    walk(path)
    return {"files": records, "directories": sorted(directories)}


def backup(path, destination):
    before = non_git(path)
    archive = destination / (path.name + ".zip")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as zipped:
        for directory in before["directories"]:
            zipped.writestr(directory + "/", b"")
        for entry in before["files"]:
            zipped.write(path / entry["path"], entry["path"])
    with zipfile.ZipFile(archive) as zipped:
        require(zipped.testzip() is None, "ZIP CRC failure")
        expected = {e["path"] for e in before["files"]}
        expected.update(d + "/" for d in before["directories"])
        require(len(zipped.namelist()) == len(expected) and set(zipped.namelist()) == expected,
                "ZIP membership mismatch")
        for entry in before["files"]:
            with zipped.open(entry["path"]) as stream:
                h = hashlib.sha256()
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(block)
            require(h.hexdigest() == entry["sha256"], "ZIP member hash mismatch")
    require(non_git(path) == before, f"Source changed during backup: {path}")
    manifest = {"source": path.as_posix(), "archive": archive.as_posix(),
                "sha256": sha(archive), "bytes": archive.stat().st_size,
                "source_unchanged": True, "zip_members_verified": True, **before}
    manifest_path = destination / (path.name + ".manifest.json")
    write_new(manifest_path, manifest)
    return {"manifest": manifest_path.as_posix(), "manifest_sha256": sha(manifest_path),
            "archive": archive.as_posix(), "sha256": manifest["sha256"],
            "archive_bytes": manifest["bytes"], "files": len(before["files"]),
            "raw_bytes": sum(e["bytes"] for e in before["files"])}


def expected_refs(manifest):
    expected = {(e["location"], e["original_ref"]): e["sha"] for e in manifest["retirement_refs"]}
    for location in ("local", "origin"):
        expected[location, WEB] = WEB_SHA
        expected[location, INTEGRATION] = PR_HEAD
    return expected


def prepare(args):
    manifest, checks = archives()  # MUST precede inventory/backup creation.
    require(args.label.isascii() and args.label.replace("-", "").isalnum(), "Unsafe label")
    require(EXTERNAL.parent.is_dir(), "External parent missing")
    EXTERNAL.mkdir(exist_ok=True)
    destination = EXTERNAL / args.label
    destination.mkdir()  # Never overwrite a prior snapshot.
    before, remote = refs()
    expected = expected_refs(manifest)
    decisions = []
    for location, live in (("local", {k: v for k, v in before.items() if k.startswith("refs/heads/")}),
                           ("origin", remote)):
        for ref, tip in sorted(live.items()):
            if ref.startswith("refs/heads/p4/"):
                decision = "KEEP-ACTIVE-P4"
            elif ref == "refs/heads/main":
                decision = "KEEP-MAIN"
            elif expected.get((location, ref)) != tip:
                decision = "KEEP-BLOCKED-unrecognized-or-advanced-head"
            else:
                decision = "CANDIDATE-after-green-merge-and-fresh-preservation-check"
            decisions.append(dict(location=location, ref=ref, sha=tip, decision=decision))
    trees = worktrees()
    for tree in trees:
        path = Path(tree["worktree"])
        branch = tree.get("branch", "")
        if path.name == "resense-cross-ring-base":
            tree["decision"] = "KEEP-EXCLUDED-missing-prunable-registration-do-not-touch"
            continue
        tree["exists"] = path.is_dir()
        if not tree["exists"]:
            tree["decision"] = "KEEP-BLOCKED-missing"
            continue
        entries = status(path)
        tree["status"] = entries
        tree["counts"] = {"tracked": sum(e["status"] not in {"??", "!!"} for e in entries),
                          "untracked": sum(e["status"] == "??" for e in entries),
                          "ignored": sum(e["status"] == "!!" for e in entries)}
        if branch.startswith("refs/heads/p4/") or path.name.startswith("rs-p4-"):
            tree["decision"] = "KEEP-ACTIVE-P4"
        elif branch == "refs/heads/main":
            tree["decision"] = "KEEP-MAIN"
        elif not branch or expected.get(("local", branch)) != tree["HEAD"]:
            tree["decision"] = "KEEP-BLOCKED-unrecognized-or-advanced-head"
        else:
            tree["decision"] = "CANDIDATE-after-green-merge-and-fresh-preservation-check"
            tree["blockers"] = [e for e in entries if e["status"] != "!!"]
            web_manifest = json.loads((EVIDENCE / "web_ci/retirement/manifest.json").read_bytes())
            web_files = {e["path"]: e for e in web_manifest["files"]}
            for entry in entries:
                if entry["status"] != "!!":
                    continue
                relative = entry["path"]
                cache = bool(set(Path(relative).parts) & {"__pycache__", ".pytest_cache", ".ruff_cache"})
                cache = cache or relative.endswith((".pyc", ".pyd", ".so"))
                known_web = branch == WEB and relative in web_files and sha(path / relative) == web_files[relative]["sha256"]
                if not cache and not known_web:
                    tree["blockers"].append(entry)
            try:
                tree["backup"] = backup(path, destination)
            except (ValueError, OSError) as error:
                tree["backup_error"] = str(error)
                tree["decision"] = "KEEP-BLOCKED-backup-incomplete"
            if tree["blockers"]:
                tree["decision"] = "KEEP-BLOCKED-uncommitted-or-unrecognized-owner-work"
            require(status(path) == entries, f"Status changed during backup: {path}")
    after, remote_after = refs()
    require(before == after and remote == remote_after, "Refs changed during snapshot; review and rerun")
    pr = json.loads(run("gh", "pr", "view", "33", "--json",
                        "number,state,headRefOid,baseRefName,mergeCommit,statusCheckRollup"))
    report = {"schema": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
              "head": decode(git("rev-parse", "HEAD")).strip(), "archives": checks,
              "pr33": pr, "refs": decisions, "all_local_and_tracking_refs": before,
              "live_origin_heads": remote, "worktrees": trees,
              "source_refs_unchanged": True, "deletion_performed": False,
              "snapshot_directory": destination.as_posix()}
    write_new(destination / "inventory.json", report)
    if args.record:
        write_new(HERE / "inventory.json", report)
    print(json.dumps({"inventory": (destination / "inventory.json").as_posix(),
                      "worktrees": [{k: w[k] for k in ("worktree", "decision", "counts", "backup") if k in w}
                                    for w in trees]}, indent=2))


def postmerge(args):
    """Read-only ancestry/archive/CI gate, not permission to remove any worktree."""
    pr = json.loads(run("gh", "pr", "view", "33", "--json",
                        "state,headRefOid,baseRefName,mergeCommit,statusCheckRollup"))
    require(pr["state"] == "MERGED" and pr["baseRefName"] == "main", "PR33 is not merged into main")
    require(pr["headRefOid"] == args.pr_head, "PR head differs from explicitly reviewed head")
    require(len(args.pr_head) == 40 and all(c in "0123456789abcdef" for c in args.pr_head), "Need full SHA")
    checks = pr["statusCheckRollup"]
    require(checks and all((c.get("status") == "COMPLETED" and c.get("conclusion") == "SUCCESS")
                          or c.get("state") == "SUCCESS" for c in checks), "PR checks are not all green")
    _, remote = refs()
    main = remote["refs/heads/main"]
    require(decode(git("rev-parse", "origin/main")).strip() == main,
            "origin/main is stale; parent must fetch it without pruning, then rerun")
    manifest, check = archives(main)
    for tip in (args.pr_head, manifest["prerequisite"]["sha"], WEB_SHA, pr["mergeCommit"]["oid"]):
        git("merge-base", "--is-ancestor", tip, main)
    print(json.dumps({"main": main, "pr_head": args.pr_head, "checks": check,
                      "remaining_gate": "Parent must restore bundle from final main and refresh/review worktree backups; no deletion authorized by this output."}, indent=2))


def verify_backup(args):
    report = json.loads(args.inventory.read_bytes())
    matches = [w for w in report["worktrees"] if w["worktree"] == args.worktree]
    require(len(matches) == 1, "Worktree not uniquely recorded")
    tree = matches[0]
    require(tree["decision"].startswith("CANDIDATE-"), "KEEP/blocked snapshot cannot authorize retirement")
    path = Path(args.worktree)
    current = [w for w in worktrees() if w["worktree"] == args.worktree]
    require(len(current) == 1 and current[0]["HEAD"] == tree["HEAD"]
            and current[0].get("branch") == tree.get("branch"), "Worktree head/branch drift")
    require(not any(e["status"] != "!!" for e in status(path)), "Tracked/untracked owner work: KEEP")
    recorded = tree["backup"]
    manifest_path = Path(recorded["manifest"])
    require(sha(manifest_path) == recorded["manifest_sha256"], "Backup manifest drift")
    manifest = json.loads(manifest_path.read_bytes())
    archive = Path(manifest["archive"])
    require(sha(archive) == manifest["sha256"] == recorded["sha256"], "Backup ZIP drift")
    require(non_git(path) == {k: manifest[k] for k in ("files", "directories")},
            "Non-Git bytes, metadata or paths changed: KEEP and take a new snapshot")
    print(json.dumps({"verified_worktree": args.worktree, "head": tree["HEAD"],
                      "backup": recorded, "deletion_performed": False}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("prepare")
    capture.add_argument("--label", required=True, help="New external snapshot directory basename")
    capture.add_argument("--record", action="store_true", help="Create owned inventory.json once")
    gate = commands.add_parser("postmerge-check")
    gate.add_argument("--pr-head", required=True, help="Explicitly owner-reviewed full merged PR SHA")
    verify = commands.add_parser("verify-backup")
    verify.add_argument("--inventory", type=Path, required=True)
    verify.add_argument("--worktree", required=True, help="Exact absolute path from inventory")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args)
    elif args.command == "postmerge-check":
        postmerge(args)
    else:
        verify_backup(args)


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    main()
