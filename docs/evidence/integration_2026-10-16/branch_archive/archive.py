"""Non-destructive branch inventory, incremental bundle, and independent restore proof.

Only generated evidence in this directory and a NEW scratch repository are written.
Git status inspects names/metadata, never the contents of untracked/ignored files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
INTEGRATION = "refs/heads/integration/2026-10-15-16"
BUNDLE = "retired-heads.bundle"
MANIFEST = "manifest.json"
LIMIT = 100_000_000  # Deliberately stricter than GitHub's 100 MiB ceiling.
EVIDENCE_FILES = (
    ".gitattributes", "README.md", "archive.py", "test_archive.py", MANIFEST,
    BUNDLE, "restore_proof.json", "preservation_postcheck.json",
)


def utc():
    return datetime.now(timezone.utc).isoformat()


def git(repo, *args, accepted=(0,)):
    repo = Path(repo).resolve()
    command = ["git", "-c", f"safe.directory={repo.as_posix()}", "-C", str(repo), *args]
    result = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}, check=False,
    )
    if result.returncode not in accepted:
        raise RuntimeError(
            f"Git failed ({result.returncode}): {command!r}\n"
            + result.stderr.decode("utf-8", "replace")
        )
    return result


def text(repo, *args):
    return git(repo, *args).stdout.decode("utf-8", "surrogateescape").strip()


def write_json(name, data):
    # Generated evidence, not an edit to application or another owner's files.
    (HERE / name).write_text(
        json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n"
    )


def ancestor(repo, old, new):
    return git(repo, "merge-base", "--is-ancestor", old, new, accepted=(0, 1)).returncode == 0


def refs(repo):
    result = {}
    for line in text(
        repo, "for-each-ref", "--format=%(refname)%09%(objectname)",
        "refs/heads", "refs/remotes/origin",
    ).splitlines():
        name, sha = line.split("\t")
        result[name] = sha
    return result


def remote_heads(repo):
    return dict(
        (name, sha) for sha, name in (
            line.split("\t") for line in text(repo, "ls-remote", "--heads", "origin").splitlines()
        )
    )


def classification(path, status):
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    if status == "!!" and (
        any(part in {"__pycache__", ".pytest_cache", ".ruff_cache"} for part in parts)
        or normalized.endswith((".pyc", ".pyd", ".so"))
    ):
        return "known-compiled-or-cache-metadata-retain"
    return "unfamiliar-or-owner-work-retain-review-before-any-cleanup"


def status_metadata(path):
    raw = git(path, "status", "--porcelain=v1", "-z", "--untracked-files=all",
              "--ignored=traditional").stdout.decode("utf-8", "surrogateescape")
    tokens = iter(raw.split("\0"))
    entries = []
    for token in tokens:
        if not token:
            continue
        status, relative = token[:2], token[3:]
        item = {"status": status, "path": relative, "classification": classification(relative, status)}
        if "R" in status or "C" in status:
            item["original_path"] = next(tokens)
        target = Path(path) / relative
        try:
            stat = target.lstat()
            item.update(bytes=stat.st_size, mtime_ns=stat.st_mtime_ns,
                        kind="symlink" if target.is_symlink() else "directory" if target.is_dir() else "file")
        except FileNotFoundError:
            item["kind"] = "absent"
        entries.append(item)
    return entries


def worktrees(repo):
    result = []
    for block in text(repo, "worktree", "list", "--porcelain").split("\n\n"):
        item = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            item[key] = value if value else True
        path = Path(item["worktree"])
        if path.name == "resense-cross-ring-base" and "detached" in item:
            item["scope"] = "excluded-older-unrelated-detached-no-retirement"
        elif item.get("branch") in {"refs/heads/main", INTEGRATION}:
            item["scope"] = "separate-future-cleanup-not-retired"
        elif "detached" in item:
            item["scope"] = "associated-detached-review-required-no-automatic-retirement"
        else:
            item["scope"] = "associated-with-retirement-ref-retain-pending-merge-and-review"
        item["exists"] = path.is_dir()
        if item["exists"] and not item["scope"].startswith("excluded-"):
            item["status"] = status_metadata(path)
        result.append(item)
    return result


def parse_bundle_header(path):
    prerequisites, heads = [], {}
    with Path(path).open("rb") as stream:
        signature = stream.readline().decode("ascii").rstrip("\n")
        if signature != "# v2 git bundle":
            raise ValueError(f"Unexpected bundle signature: {signature!r}")
        while True:
            line = stream.readline()
            if line == b"\n":
                break
            if not line or len(line) > 65536:
                raise ValueError("Invalid bundle header")
            value = line.decode("utf-8").rstrip("\n")
            if value.startswith("-"):
                sha, _, subject = value[1:].partition(" ")
                prerequisites.append({"sha": sha, "subject": subject})
            else:
                sha, name = value.split(" ", 1)
                if name in heads:
                    raise ValueError(f"Duplicate bundle ref: {name}")
                heads[name] = sha
        if stream.read(4) != b"PACK":
            raise ValueError("Missing pack after bundle header")
    return {"signature": signature, "prerequisites": prerequisites, "heads": heads}


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def validate_contract(manifest, header, actual_sha256, actual_bytes):
    """Validate independent byte/header/manifest evidence before importing a pack."""
    if manifest["schema"] != 1:
        raise ValueError("Unsupported manifest schema")
    if actual_sha256 != manifest["bundle"]["sha256"] or actual_bytes != manifest["bundle"]["bytes"]:
        raise ValueError("Bundle hash/size mismatch")
    if not 0 < actual_bytes < LIMIT:
        raise ValueError("Bundle exceeds committed single-file size contract")
    if header != manifest["bundle"]["header"]:
        raise ValueError("Bundle header differs from frozen manifest")
    if not header["prerequisites"]:
        raise ValueError("Expected incremental bundle prerequisites")
    seed = manifest["prerequisite"]["sha"]
    if len(seed) != 40 or any(c not in "0123456789abcdef" for c in seed):
        raise ValueError("Invalid frozen seed SHA")
    excluded = {"refs/heads/main", INTEGRATION, "refs/remotes/origin/main", "refs/remotes/origin/HEAD"}
    expected_refs = {name: sha for name, sha in manifest["refs_before"].items() if name not in excluded}
    names = set()
    advertised = set()
    for entry in manifest["retirement_refs"]:
        name, sha = entry["archive_ref"], entry["sha"]
        if name in names or name in excluded:
            raise ValueError("Duplicate or excluded retirement ref")
        if expected_refs.get(name) != sha:
            raise ValueError("Retirement ref differs from original inventory")
        remote = entry["location"] == "origin"
        original = name.replace("refs/remotes/origin/", "refs/heads/", 1) if remote else name
        if original != entry["original_ref"]:
            raise ValueError("Original namespace mapping mismatch")
        if remote and manifest["origin_heads_before"].get(original) != sha:
            raise ValueError("Retirement ref differs from live origin inventory")
        names.add(name)
        if entry["preservation"] == "advertised-in-bundle":
            if header["heads"].get(name) != sha:
                raise ValueError(f"Exact retired tip not advertised: {name}")
            advertised.add(name)
        elif entry["preservation"] == "ancestor-of-frozen-prerequisite":
            if entry["ancestor_of"] != seed or name in header["heads"]:
                raise ValueError("Invalid prerequisite preservation claim")
        else:
            raise ValueError("Unknown preservation mode")
    if advertised != set(header["heads"]):
        raise ValueError("Unaccounted advertised bundle refs")
    if names != set(expected_refs):
        raise ValueError("Original retirement inventory is incomplete")
    expected_origin = {name: sha for name, sha in manifest["origin_heads_before"].items() if name != "refs/heads/main"}
    actual_origin = {e["original_ref"]: e["sha"] for e in manifest["retirement_refs"] if e["location"] == "origin"}
    if expected_origin != actual_origin:
        raise ValueError("Original origin inventory is incomplete")
    counts = {
        "retirement_refs": len(names),
        "local_heads": sum(e["location"] == "local" for e in manifest["retirement_refs"]),
        "origin_heads": len(actual_origin),
        "unique_retired_tips": len({e["sha"] for e in manifest["retirement_refs"]}),
        "advertised_refs": len(advertised),
        "prerequisite_covered_refs": len(names) - len(advertised),
    }
    if manifest["counts"] != counts:
        raise ValueError("Retirement count mismatch")


def file_inventory():
    return {name: {"sha256": digest(HERE / name), "bytes": (HERE / name).stat().st_size}
            for name in EVIDENCE_FILES}


def check(repo, verify_files=True):
    manifest = json.loads((HERE / MANIFEST).read_text(encoding="utf-8"))
    path = HERE / manifest["bundle"]["file"]
    header = parse_bundle_header(path)
    validate_contract(manifest, header, digest(path), path.stat().st_size)
    seed = manifest["prerequisite"]["sha"]
    for prerequisite in header["prerequisites"]:
        if not ancestor(repo, prerequisite["sha"], seed):
            raise ValueError("Bundle prerequisite outside frozen seed ancestry")
    for entry in manifest["retirement_refs"]:
        if entry["preservation"] == "ancestor-of-frozen-prerequisite" and not ancestor(repo, entry["sha"], seed):
            raise ValueError(f"False ancestry claim: {entry['archive_ref']}")
    verify = git(repo, "bundle", "verify", str(path))
    listed = dict(
        (name, sha) for sha, name in (
            line.split(" ", 1) for line in text(repo, "bundle", "list-heads", str(path)).splitlines()
        )
    )
    if listed != header["heads"]:
        raise ValueError("git bundle list-heads disagrees with header")
    sealed_files = HERE / "file_manifest.json"
    if verify_files and sealed_files.exists():
        if json.loads(sealed_files.read_text(encoding="utf-8"))["files"] != file_inventory():
            raise ValueError("Evidence file checksum/size mismatch; do not silently reseal an altered archive")
    return manifest, {
        "sha256": digest(path), "bytes": path.stat().st_size,
        "bundle_verify_stdout": verify.stdout.decode("utf-8", "replace"),
        "bundle_verify_stderr": verify.stderr.decode("utf-8", "replace"),
        "list_heads": listed,
    }


def restore(source, scratch, record):
    scratch = Path(scratch).resolve()
    if scratch.exists() or not scratch.parent.is_dir():
        raise ValueError("Scratch must be NEW and its parent must already exist")
    manifest, checks = check(source)
    seed = manifest["prerequisite"]["sha"]
    git(scratch.parent, "init", "--bare", str(scratch))
    git(scratch, "fetch", "--no-tags", "--no-write-fetch-head", str(Path(source).resolve()),
        f"{seed}:refs/archive/frozen-prerequisite")
    if (scratch / "objects" / "info" / "alternates").exists():
        raise ValueError("Restore must not borrow source objects via alternates")
    pre_import = {}
    for entry in manifest["retirement_refs"]:
        result = git(scratch, "cat-file", "-e", f"{entry['sha']}^{{commit}}", accepted=(0, 128))
        pre_import[entry["archive_ref"]] = result.returncode == 0
        expected = entry["preservation"] == "ancestor-of-frozen-prerequisite"
        if pre_import[entry["archive_ref"]] != expected:
            raise ValueError("Seed-only availability disagrees with manifest")
    # Verify in the actual independent repository before importing unique history.
    git(scratch, "bundle", "verify", str(HERE / BUNDLE))
    imported = text(scratch, "bundle", "unbundle", str(HERE / BUNDLE))
    restored = []
    for entry in manifest["retirement_refs"]:
        sha, name = entry["sha"], entry["archive_ref"]
        git(scratch, "cat-file", "-e", f"{sha}^{{commit}}")
        git(scratch, "cat-file", "-e", f"{sha}^{{tree}}")
        git(scratch, "update-ref", name, sha)  # SCRATCH ONLY, original namespace.
        if text(scratch, "rev-parse", name) != sha:
            raise ValueError("Scratch ref mismatch")
        restored.append({"archive_ref": name, "sha": sha, "commit_and_tree_present": True})
    fsck = git(scratch, "fsck", "--full", "--no-reflogs")
    proof = {
        "created_utc": utc(), "source_read_only": str(Path(source).resolve()),
        "scratch_bare_repository": str(scratch), "prerequisite": seed,
        "source_fetch_refspec": f"{seed}:refs/archive/frozen-prerequisite",
        "no_alternates": True, "checks": checks, "seed_only_availability": pre_import,
        "unbundle_stdout": imported, "restored_refs": restored,
        "fsck_exit": fsck.returncode, "fsck_stdout": fsck.stdout.decode("utf-8", "replace"),
        "fsck_stderr": fsck.stderr.decode("utf-8", "replace"),
        "git_version": text(source, "--version"), "python_version": sys.version,
    }
    if record:
        write_json("restore_proof.json", proof)
    return proof


def create(seed, scratch):
    if (HERE / MANIFEST).exists() or (HERE / BUNDLE).exists():
        raise ValueError("Refusing to overwrite an existing frozen archive")
    if text(ROOT, "symbolic-ref", "HEAD") != INTEGRATION:
        raise ValueError("Archive creation requires the shared integration worktree")
    if len(seed) != 40 or not ancestor(ROOT, seed, "HEAD"):
        raise ValueError("Explicit full frozen prerequisite must be an ancestor of HEAD")
    before_refs = refs(ROOT)
    before_remote = remote_heads(ROOT)
    for name, sha in before_remote.items():
        cached = name.replace("refs/heads/", "refs/remotes/origin/", 1)
        if before_refs.get(cached) != sha:
            raise ValueError(f"Origin inventory differs from local object inventory: {name}")
    excluded = {"refs/heads/main", INTEGRATION, "refs/remotes/origin/main", "refs/remotes/origin/HEAD"}
    retired = []
    for name, sha in sorted(before_refs.items()):
        if name in excluded:
            continue
        is_remote = name.startswith("refs/remotes/origin/")
        original = name.replace("refs/remotes/origin/", "refs/heads/", 1) if is_remote else name
        if is_remote and before_remote.get(original) != sha:
            raise ValueError(f"Stale origin tracking ref requires explicit review: {name}")
        retired.append({
            "location": "origin" if is_remote else "local", "original_ref": original,
            "archive_ref": name, "sha": sha,
            "note": "stale LOCAL only; remote already deleted by user; retain unique history"
                    if name == "refs/heads/experiment/cross-ring-sparse-evidence" else
                    "REJECTED candidate; preserve history, do not enable"
                    if original == "refs/heads/r3/axis-B-trial" else "preserve original tip",
        })
    before_worktrees = worktrees(ROOT)
    # All retirement refs, not just the currently known unmerged ones. Git decides
    # which refs are actually advertised after excluding the frozen seed ancestry.
    command = ["bundle", "create", "--version=2", str(HERE / BUNDLE)]
    command.extend(entry["archive_ref"] for entry in retired)
    command.extend(["--not", seed])
    git(ROOT, *command)
    header = parse_bundle_header(HERE / BUNDLE)
    for entry in retired:
        if ancestor(ROOT, entry["sha"], seed):
            entry.update(preservation="ancestor-of-frozen-prerequisite", ancestor_of=seed)
        elif header["heads"].get(entry["archive_ref"]) == entry["sha"]:
            entry["preservation"] = "advertised-in-bundle"
        else:
            raise ValueError(f"Unpreserved retired tip: {entry}")
    manifest = {
        "schema": 1, "created_utc": utc(), "source_worktree": str(ROOT),
        "source_common_git_dir": text(ROOT, "rev-parse", "--path-format=absolute", "--git-common-dir"),
        "prerequisite": {
            "sha": seed, "role": "frozen exclusion tip and required restore seed",
            "must_remain_ancestor_of_final_main": True,
            "header_boundary_note": "Git records boundary commits, not necessarily the exclusion tip; every header prerequisite is verified as an ancestor of this frozen seed.",
        },
        "bundle": {"file": BUNDLE, "sha256": digest(HERE / BUNDLE),
                   "bytes": (HERE / BUNDLE).stat().st_size, "header": header,
                   "create_git_arguments": command},
        "counts": {"retirement_refs": len(retired),
                   "local_heads": sum(e["location"] == "local" for e in retired),
                   "origin_heads": sum(e["location"] == "origin" for e in retired),
                   "unique_retired_tips": len({e["sha"] for e in retired}),
                   "advertised_refs": len(header["heads"]),
                   "prerequisite_covered_refs": sum(e["preservation"] == "ancestor-of-frozen-prerequisite" for e in retired)},
        "retirement_refs": retired,
        "excluded_refs": {name: before_refs[name] for name in sorted(excluded)},
        "refs_before": before_refs, "origin_heads_before": before_remote,
        "worktrees_before": before_worktrees,
        "cleanup_constraints": [
            "No source branch, tag, worktree, config, remote or data removal or modification.",
            "Main and current integration branch require separate future cleanup review.",
            "Older unrelated detached resense-cross-ring-base is excluded, including pruning.",
            "Data/cache/raw directories outside worktrees are outside cleanup scope.",
            "Ignored compiled/cache metadata is inventoried, not permission to delete it.",
            "Every untracked/modified/unfamiliar path must be retained and owner-reviewed before worktree removal.",
            "Retirement requires verified normal main merge, tracked bundle, unchanged-or-main-ancestor live heads and fresh worktree review.",
        ],
    }
    validate_contract(manifest, header, digest(HERE / BUNDLE), (HERE / BUNDLE).stat().st_size)
    write_json(MANIFEST, manifest)
    proof = restore(manifest["source_common_git_dir"], scratch, record=True)
    print(json.dumps({"counts": manifest["counts"], "bundle": {k: manifest["bundle"][k] for k in ("file", "sha256", "bytes")},
                      "prerequisite": seed, "restore_fsck_exit": proof["fsck_exit"]}, indent=2))


def postcheck():
    manifest, checks = check(ROOT, verify_files=False)
    after_refs, after_remote, after_worktrees = refs(ROOT), remote_heads(ROOT), worktrees(ROOT)
    changes = []
    for entry in manifest["retirement_refs"]:
        if after_refs.get(entry["archive_ref"]) != entry["sha"]:
            changes.append({"ref": entry["archive_ref"], "before": entry["sha"], "after": after_refs.get(entry["archive_ref"])})
        if entry["location"] == "origin" and after_remote.get(entry["original_ref"]) != entry["sha"]:
            changes.append({"origin_ref": entry["original_ref"], "before": entry["sha"], "after": after_remote.get(entry["original_ref"])})
    if after_refs.get("refs/heads/main") != manifest["excluded_refs"]["refs/heads/main"]:
        changes.append({"ref": "refs/heads/main", "issue": "main changed during archive preparation"})
    for name in sorted(set(after_refs) - set(manifest["refs_before"])):
        changes.append({"new_ref_requires_inventory": name, "sha": after_refs[name]})
    for name in sorted(set(after_remote) - set(manifest["origin_heads_before"])):
        changes.append({"new_origin_head_requires_inventory": name, "sha": after_remote[name]})
    seed_is_ancestor = ancestor(ROOT, manifest["prerequisite"]["sha"], "HEAD")
    before_paths = {item["worktree"] for item in manifest["worktrees_before"]}
    after_paths = {item["worktree"] for item in after_worktrees}
    metadata_changes = []
    for before in manifest["worktrees_before"]:
        after = next((w for w in after_worktrees if w["worktree"] == before["worktree"]), {})
        indexed = {item["path"]: item for item in after.get("status", [])}
        for item in before.get("status", []):
            # Own generated files and concurrent review files are inventoried too.
            current = indexed.get(item["path"])
            if current != item:
                metadata_changes.append({"worktree": before["worktree"], "before": item,
                                         "after_status_entry": current,
                                         "path_still_exists": (Path(before["worktree"]) / item["path"]).exists()})
    report = {
        "captured_utc": utc(), "head_at_check": text(ROOT, "rev-parse", "HEAD"),
        "checks": checks, "frozen_seed_is_ancestor_of_integration": seed_is_ancestor,
        "retirement_ref_changes": changes, "same_registered_worktrees": before_paths == after_paths,
        "refs_after": after_refs, "origin_heads_after": after_remote,
        "worktrees_after": after_worktrees, "prior_status_metadata_changes": metadata_changes,
        "interpretation": "Status metadata can change during concurrent H4 work and cache use; no path contents were read and no source worktree path was removed by this helper.",
    }
    write_json("preservation_postcheck.json", report)
    if changes or not seed_is_ancestor or before_paths != after_paths:
        raise ValueError("Preservation postcheck drift requires review")
    print(json.dumps({"retirement_ref_changes": changes, "same_registered_worktrees": before_paths == after_paths,
                      "prior_status_metadata_changes": len(metadata_changes), "frozen_seed_is_ancestor_of_integration": seed_is_ancestor}, indent=2))


def inventory():
    report_path = HERE / "preservation_postcheck.json"
    data = json.loads(report_path.read_text(encoding="utf-8"))
    for item in data["worktrees_after"]:
        entries = item.get("status", [])
        unknown = [e for e in entries if e["classification"].startswith("unfamiliar-")]
        print(json.dumps({
            "worktree": item["worktree"], "scope": item["scope"], "exists": item["exists"],
            "tracked_changes": sum(e["status"] not in {"??", "!!"} for e in entries),
            "untracked": sum(e["status"] == "??" for e in entries),
            "ignored": sum(e["status"] == "!!" for e in entries),
            "known_compiled_cache": len(entries) - len(unknown),
            "retain_review_paths": [{"status": e["status"], "path": e["path"]} for e in unknown],
        }))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    creation = sub.add_parser("create")
    creation.add_argument("--prerequisite", required=True)
    creation.add_argument("--scratch", required=True)
    sub.add_parser("check")
    restoration = sub.add_parser("restore")
    restoration.add_argument("--source", required=True, help="final-main clone or read-only common source")
    restoration.add_argument("--scratch", required=True)
    sub.add_parser("postcheck")
    sub.add_parser("inventory")
    sub.add_parser("seal", help="record generated evidence checksums after the final postcheck")
    args = parser.parse_args()
    if args.command == "create":
        create(args.prerequisite, args.scratch)
    elif args.command == "check":
        manifest, checks = check(ROOT)
        print(json.dumps({"counts": manifest["counts"], "checks": checks}, indent=2))
    elif args.command == "restore":
        proof = restore(args.source, args.scratch, record=False)
        print(json.dumps(proof, indent=2))
    elif args.command == "postcheck":
        postcheck()
    elif args.command == "inventory":
        inventory()
    else:
        write_json("file_manifest.json", {"algorithm": "sha256", "self_excluded": True, "files": file_inventory()})
        print("Sealed eight evidence files; file_manifest.json intentionally excludes itself.")


if __name__ == "__main__":
    main()
