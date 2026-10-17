"""Archive the separately approved October 15 image by its exact immutable ID."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
APPROVED = Path(r"D:\ReSense-actions-archive-20261016\main_image")
C_ARCHIVE = Path(r"C:\Users\alikh\AppData\Local\Temp\opencode\resense-actions-artifact-archive-20261016")
EVIDENCE = C_ARCHIVE.parent / "rs-integration-20261016/docs/evidence/integration_ci_2026-10-16/artifact_retention/main_image"
ID = 11990270962
EXPECTED = {
    "id": ID, "name": "resense-image-1.0.0-3fdc879", "size_in_bytes": 529881425,
    "digest": "sha256:d047bd5693deda64b7680991908d61dc9a53ff83e08b61b186aeb5e95e10d367",
    "created_at": "2026-10-15T16:08:07Z", "expired": False,
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def eligible(artifact):
    return (all(artifact.get(key) == value for key, value in EXPECTED.items())
            and artifact.get("workflow_run", {}).get("id") == 38765546278
            and artifact["workflow_run"].get("head_sha") == "3fdc87957f5d09ff32573eabe6637924b91ea376")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("plan", "execute", "export"))
    args = parser.parse_args()
    if ROOT != APPROVED:
        raise RuntimeError("Run only from the approved main_image archive directory")
    source = ROOT / "retain_artifacts_base.py"
    if not source.exists():
        shutil.copyfile(ROOT.parent / "retain_artifacts_base.py", source)
    if sha(source) != sha(C_ARCHIVE / "retain_artifacts.py"):
        raise RuntimeError("Original helper provenance mismatch")
    spec = importlib.util.spec_from_file_location("retention_base", source)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    base.ROOT = ROOT
    base.eligible = eligible
    if not (ROOT / "inventory-before.json").exists():
        before = base.inventory()
        selected = [a for a in before["artifacts"] if eligible(a)]
        if len(selected) != 1:
            raise RuntimeError("Expected exactly the approved October artifact")
        base.save(ROOT / "release-before.json", base.release())
        paths = [C_ARCHIVE / name for name in ("manifest.json", "summary.json", "inventory-after.json")]
        paths += [ROOT.parent / name for name in ("manifest.json", "combined-summary.json", "inventory-after.json", "local-final-verification.json")]
        base.save(ROOT / "prior-proof-hashes.json", {str(path): sha(path) for path in paths})
        base.save(ROOT / "inventory-before.json", before)
    before = read(ROOT / "inventory-before.json")
    selected = [a for a in before["artifacts"] if eligible(a)]
    if len(selected) != 1:
        raise RuntimeError("Snapshot selection mismatch")
    for path, expected in read(ROOT / "prior-proof-hashes.json").items():
        if sha(Path(path)) != expected:
            raise RuntimeError("Historical proof changed")
    preflight = {"at": base.now(), "selected_ids": [ID], "selected_bytes": 529881425,
                 "disk_free_bytes": shutil.disk_usage(ROOT).free, "reserve_bytes": base.RESERVE,
                 "decision": "Separately approved final October 15 Actions image archival; earlier remote retention decisions remain historical."}
    base.save(ROOT / "preflight.json", preflight)
    print(json.dumps(preflight), flush=True)
    if args.mode == "execute":
        base.execute(selected, 1)
        record = read(ROOT / "manifest.json")["records"][str(ID)]
        if not record.get("delete_succeeded_at") or record.get("absence_http_status") != 404:
            raise RuntimeError("Deletion not complete; inspect manifest")
    if args.mode != "plan":
        base.audit(before)
        after = read(ROOT / "inventory-after.json")
        summary = read(ROOT / "summary.json")
        prior = read(ROOT.parent / "combined-summary.json")
        summary.update({
            "remaining_artifact_bytes": sum(a["size_in_bytes"] for a in after["artifacts"]),
            "remaining_log_count": sum(a["name"].startswith("p1-cold-dry-run-") for a in after["artifacts"]),
            "cumulative_archived_image_count": prior["deleted_count"] + summary["deleted_count"],
            "cumulative_archived_image_bytes": prior["deleted_bytes"] + summary["deleted_bytes"],
            "prior_proof_unchanged": all(sha(Path(path)) == value for path, value in read(ROOT / "prior-proof-hashes.json").items()),
        })
        base.save(ROOT / "summary.json", summary)
        print(json.dumps(summary), flush=True)
    if args.mode == "export":
        if not EVIDENCE.parent.is_dir():
            raise RuntimeError("Missing evidence parent")
        EVIDENCE.mkdir(exist_ok=True)
        names = ("archive_main_image.py", "retain_artifacts_base.py", "prior-proof-hashes.json",
                 "preflight.json", "manifest.json", "local-final-verification.json", "summary.json",
                 "inventory-before.json", "inventory-after.json", "release-before.json", "release-after.json")
        for name in names:
            shutil.copyfile(ROOT / name, EVIDENCE / name)
        (EVIDENCE / "SHA256SUMS").write_text(
            "".join(f"{sha(EVIDENCE / name)}  {name}\n" for name in sorted(names)), encoding="utf-8", newline="\n")
        print(json.dumps({"evidence": str(EVIDENCE), "files": len(names) + 1}), flush=True)


if __name__ == "__main__":
    main()
