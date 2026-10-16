"""Continue the immutable September selection on approved D:, preserving C: proof.

Reuse the original verified helper, seed completed C: records exactly once, and
store new proof exclusively on D: and in a new integration evidence subdirectory.
"""
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
APPROVED = Path(r"D:\ReSense-actions-archive-20261016")
OLD = Path(r"C:\Users\alikh\AppData\Local\Temp\opencode\resense-actions-artifact-archive-20261016")
EVIDENCE = OLD.parent / "rs-integration-20261016/docs/evidence/integration_ci_2026-10-16/artifact_retention/d_continuation"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def initialize():
    if ROOT != APPROVED or not ROOT.parent.is_dir():
        raise RuntimeError("Only the approved D: archive root is permitted")
    source = ROOT / "retain_artifacts_base.py"
    if not source.exists():
        shutil.copyfile(OLD / "retain_artifacts.py", source)
    if digest(source) != digest(OLD / "retain_artifacts.py"):
        raise RuntimeError("Original helper provenance changed")
    spec = importlib.util.spec_from_file_location("retention_base", source)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    base.ROOT = ROOT
    if not (ROOT / "initialization.json").exists():
        if (ROOT / "manifest.json").exists():
            raise RuntimeError("Incomplete initialization: inspect existing manifest")
        old = read(OLD / "manifest.json")
        completed = {key: value for key, value in old["records"].items()
                     if value.get("delete_succeeded_at") and value.get("absence_http_status") == 404}
        if len(completed) != 14:
            raise RuntimeError("Expected exactly 14 completed C: archives")
        for record in completed.values():
            if Path(record["verification"]["path"]).parent != OLD:
                raise RuntimeError("Unexpected prior archive path")
        for name in ("inventory-before.json", "release-before.json"):
            shutil.copyfile(OLD / name, ROOT / name)
        base.save(ROOT / "manifest.json", {
            "repo": "pmixay/ReSense", "archive_roots": [str(OLD), str(ROOT)],
            "prior_completed_ids": sorted(completed), "records": completed})
        before = base.inventory()
        base.save(ROOT / "d-inventory-before.json", before)
        base.save(ROOT / "d-release-before.json", base.release())
        base.save(ROOT / "initialization.json", {
            "at": base.now(), "disk_free_bytes": shutil.disk_usage(ROOT).free,
            "reserve_bytes": base.RESERVE, "prior_completed_count": len(completed),
            "original_proof_hashes": {name: digest(OLD / name) for name in (
                "manifest.json", "inventory-before.json", "inventory-after.json",
                "release-before.json", "release-after.json", "summary.json",
                "local-final-verification.json", "preflight.json", "retain_artifacts.py")}})
    for name, expected in read(ROOT / "initialization.json")["original_proof_hashes"].items():
        if digest(OLD / name) != expected:
            raise RuntimeError(f"Original C: proof changed: {name}")
    return base


def prepare(base, artifact):
    path = ROOT / f"{artifact['id']}--{artifact['name']}.zip"
    if not path.exists():
        base.download(artifact, path)
    return base.verify(path, artifact)


def execute(base, candidates, limit, workers):
    records = read(ROOT / "manifest.json")["records"]
    pending = [a for a in candidates if records.get(str(a["id"]), {}).get("absence_http_status") != 404][:limit]
    for start in range(0, len(pending), workers):
        batch = pending[start:start + workers]
        needed = sum(a["size_in_bytes"] for a in batch)
        if shutil.disk_usage(ROOT).free < needed + base.RESERVE:
            raise RuntimeError("Insufficient D: capacity for batch plus 5 GiB reserve")
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(prepare, base, artifact): artifact for artifact in batch}
            for future in concurrent.futures.as_completed(futures):
                artifact = futures[future]
                try:
                    future.result()
                except Exception as error:
                    # Do not expose subprocess stderr or signed redirect URLs.
                    base.save(ROOT / f"download-failure-{artifact['id']}.json", {
                        "at": base.now(), "id": artifact["id"], "error_type": type(error).__name__})
                    raise RuntimeError(f"Download/verification failed for {artifact['id']}; remote retained") from None
                # All manifest mutation and exact-ID deletions remain serial.
                # The base helper independently re-verifies the completed ZIP.
                base.execute([artifact], 1)
                record = read(ROOT / "manifest.json")["records"][str(artifact["id"])]
                if record.get("absence_http_status") != 404:
                    raise RuntimeError(f"Deletion incomplete for {artifact['id']}; inspect manifest")
        stamp = base.now().replace(":", "-")
        manifest = read(ROOT / "manifest.json")
        base.save(ROOT / f"checkpoint-{stamp}.json", {
            "at": base.now(), "manifest_sha256": digest(ROOT / "manifest.json"),
            "completed_count": sum(r.get("absence_http_status") == 404 for r in manifest["records"].values()),
            "disk_free_bytes": shutil.disk_usage(ROOT).free})


def final_audit(base, before):
    # Fresh full ZIP hashes, member CRCs and embedded tar hashes across both disks.
    base.audit(before)
    manifest = read(ROOT / "manifest.json")
    records = list(manifest["records"].values())
    completed = [r for r in records if r.get("delete_succeeded_at") and r.get("absence_http_status") == 404]
    final = read(ROOT / "inventory-after.json")
    remaining = {a["id"] for a in final["artifacts"]}
    eligible = {a["id"] for a in before["artifacts"] if base.eligible(a)}
    original_ids = {a["id"] for a in before["artifacts"]}
    d_before = read(ROOT / "d-inventory-before.json")
    new_before_ids = {a["id"] for a in d_before["artifacts"]} - original_ids
    report = read(ROOT / "summary.json")
    report.update({
        "archive_roots": [str(OLD), str(ROOT)],
        "c_archive_count": sum(Path(r["verification"]["path"]).parent == OLD for r in completed),
        "d_archive_count": sum(Path(r["verification"]["path"]).parent == ROOT for r in completed),
        "d_archive_bytes": sum(r["verification"]["zip_bytes"] for r in completed if Path(r["verification"]["path"]).parent == ROOT),
        "remaining_original_eligible_ids": sorted(eligible & remaining),
        "new_artifacts_since_original_snapshot": sorted(remaining - original_ids),
        "new_artifacts_present_at_d_start_missing": sorted(new_before_ids - remaining),
        "original_c_proof_unchanged": all(digest(OLD / name) == value for name, value in read(ROOT / "initialization.json")["original_proof_hashes"].items()),
        "all_original_85_complete": len(completed) == 85 and not (eligible & remaining),
    })
    base.save(ROOT / "combined-summary.json", report)
    print(json.dumps(report), flush=True)


def export(base):
    if not EVIDENCE.parent.is_dir():
        raise RuntimeError("Missing integration evidence parent")
    EVIDENCE.mkdir(exist_ok=True)
    names = ["continue_retention.py", "retain_artifacts_base.py", "initialization.json",
             "manifest.json", "combined-summary.json", "local-final-verification.json",
             "preflight.json", "d-release-before.json", "release-after.json"]
    for name in names:
        shutil.copyfile(ROOT / name, EVIDENCE / name)
    for name in ("d-inventory-before.json", "inventory-after.json"):
        data = read(ROOT / name)
        base.save(EVIDENCE / name, {
            "at": data["at"], "count": len(data["artifacts"]),
            "page_counts": [len(p["artifacts"]) for p in data["pages"]],
            "full_external_snapshot_sha256": digest(ROOT / name),
            "artifacts": [{key: a.get(key) for key in (
                "id", "name", "size_in_bytes", "digest", "created_at", "expired", "workflow_run")}
                for a in data["artifacts"]]})
        names.append(name)
    checksum_text = "".join(f"{digest(EVIDENCE / name)}  {name}\n" for name in sorted(names))
    (EVIDENCE / "SHA256SUMS").write_text(checksum_text, encoding="utf-8", newline="\n")
    print(json.dumps({"evidence": str(EVIDENCE), "files": len(names) + 1}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("plan", "execute", "audit", "export"))
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--workers", type=int, choices=(1, 2, 3), default=3)
    args = parser.parse_args()
    base = initialize()
    before, candidates = base.snapshot()
    if args.mode == "execute":
        execute(base, candidates, args.limit, args.workers)
    if args.mode in ("audit", "export"):
        final_audit(base, before)
    if args.mode == "export":
        export(base)


if __name__ == "__main__":
    main()
