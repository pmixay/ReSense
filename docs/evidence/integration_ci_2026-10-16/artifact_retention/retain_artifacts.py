"""Archive approved historical ReSense Actions ZIPs before exact-ID deletion.

Standard library + authenticated gh. No extraction, release mutation, or tokens
in argv/logs. Snapshot scope is immutable; future artifacts are never candidates.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
APPROVED_ROOT = Path(r"C:\Users\alikh\AppData\Local\Temp\opencode\resense-actions-artifact-archive-20261016")
REPO = "repos/pmixay/ReSense"
RESERVE = 5 * 1024**3


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def save(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def api(endpoint, method="GET", missing_ok=False):
    result = subprocess.run(
        ["gh", "api", "--method", method, endpoint], capture_output=True
    )
    if result.returncode:
        if missing_ok and b"(HTTP 404)" in result.stderr:
            return None
        raise RuntimeError(f"gh {method} failed for {endpoint}: exit {result.returncode}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def inventory():
    pages = []
    page = 1
    while True:
        response = api(f"{REPO}/actions/artifacts?per_page=100&page={page}")
        pages.append(response)
        if len(response["artifacts"]) < 100:
            break
        page += 1
    artifacts = [a for p in pages for a in p["artifacts"]]
    if len({a["id"] for a in artifacts}) != len(artifacts):
        raise RuntimeError("Pagination duplicated IDs; retry snapshot")
    if len(artifacts) != pages[0]["total_count"]:
        raise RuntimeError("Inventory changed during pagination; retry snapshot")
    return {"at": now(), "pages": pages, "artifacts": artifacts}


def release():
    data = api(f"{REPO}/releases/tags/v1.0.0")
    return {"id": data["id"], "tag_name": data["tag_name"], "assets": [
        {key: asset.get(key) for key in ("id", "name", "size", "digest")}
        for asset in data["assets"]
    ]}


def eligible(artifact):
    return (re.fullmatch(r"resense-image-1\.0\.0-[0-9a-f]{7}", artifact["name"])
            and "2026-09-24" <= artifact["created_at"] < "2026-09-30"
            and not artifact["expired"])


def snapshot():
    path = ROOT / "inventory-before.json"
    if not path.exists():
        data = inventory()
        save(path, data)
        save(ROOT / "release-before.json", release())
    data = json.loads(path.read_text(encoding="utf-8"))
    candidates = sorted((a for a in data["artifacts"] if eligible(a)),
                        key=lambda a: (a["created_at"], a["id"]))
    free = shutil.disk_usage(ROOT).free
    report = {"at": now(), "inventory_count": len(data["artifacts"]),
              "candidate_count": len(candidates),
              "candidate_bytes": sum(a["size_in_bytes"] for a in candidates),
              "protected_count": len(data["artifacts"]) - len(candidates),
              "disk_free_bytes": free, "reserve_bytes": RESERVE,
              "download_capacity_bytes": max(0, free - RESERVE),
              "policy": "September 24-29 v1.0.0 images only; retain October main image, all logs, releases, new artifacts"}
    save(ROOT / "preflight.json", report)
    print(json.dumps(report), flush=True)
    return data, candidates


def hash_stream(stream):
    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(4 * 1024**2):
        size += len(chunk)
        digest.update(chunk)
    return size, digest.hexdigest()


def verify(path, artifact):
    if path.stat().st_size != artifact["size_in_bytes"]:
        raise RuntimeError("ZIP byte count differs from API metadata")
    expected = artifact.get("digest") or ""
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", expected):
        raise RuntimeError("Missing/unsupported API SHA256; remote retained")
    with path.open("rb") as stream:
        size, digest = hash_stream(stream)
    if "sha256:" + digest != expected:
        raise RuntimeError("ZIP SHA256 differs from API digest")
    members = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names):
            raise RuntimeError("Duplicate ZIP member names")
        tar_names = [name for name in names if name.endswith(".tar.gz")]
        if not tar_names:
            raise RuntimeError("No embedded tar.gz")
        for name in tar_names:
            checksum_name = name + ".sha256"
            if checksum_name not in names:
                raise RuntimeError("Missing embedded tar.gz SHA256 sidecar")
            if archive.getinfo(checksum_name).file_size > 65536:
                raise RuntimeError("Unexpectedly large checksum sidecar")
            text = archive.read(checksum_name).decode("utf-8").strip()
            match = re.fullmatch(r"([0-9a-fA-F]{64}) [ *](.+)", text)
            if not match or match[2] not in (name, Path(name).name):
                raise RuntimeError("Invalid embedded checksum or filename")
            with archive.open(name) as stream:
                tar_size, tar_digest = hash_stream(stream)
            if tar_digest != match[1].lower():
                raise RuntimeError("Embedded tar.gz SHA256 mismatch")
            members.append({"name": name, "bytes": tar_size, "sha256": tar_digest,
                            "checksum_member": checksum_name, "crc_verified": True})
        # Every member is read to EOF: ZipExtFile checks CRC, including the tar
        # above. No second disk copy or uncompressed image is created.
        for item in archive.infolist():
            if item.filename not in tar_names:
                with archive.open(item) as stream:
                    hash_stream(stream)
    return {"verified_at": now(), "zip_bytes": size, "zip_sha256": digest,
            "api_sha256_match": True, "zip_crc_all_members": True,
            "embedded_tar_checksums": members, "path": str(path)}


def download(artifact, path):
    partial = path.with_suffix(".zip.partial")
    free = shutil.disk_usage(ROOT).free
    if free < artifact["size_in_bytes"] + RESERVE:
        raise RuntimeError("Disk reserve: insufficient space for another retained ZIP")
    # gh follows the API's signed redirect and writes unchanged binary stdout.
    # Authentication remains in gh's keyring; never obtain or print the token.
    with partial.open("xb") as stream:
        result = subprocess.run(
            ["gh", "api", f"{REPO}/actions/artifacts/{artifact['id']}/zip"],
            stdout=stream, stderr=subprocess.PIPE, timeout=1800,
        )
        stream.flush()
        os.fsync(stream.fileno())
    if result.returncode:
        raise RuntimeError(f"ZIP download failed: gh exit {result.returncode}")
    partial.replace(path)


def execute(candidates, limit):
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {
        "repo": "pmixay/ReSense", "archive_root": str(ROOT), "records": {}}
    processed = 0
    for artifact in candidates:
        key = str(artifact["id"])
        previous = manifest["records"].get(key, {})
        if previous.get("absence_http_status") == 404:
            continue
        if processed >= limit:
            break
        processed += 1
        record = {"artifact": artifact, **previous}
        manifest["records"][key] = record
        path = ROOT / f"{key}--{artifact['name']}.zip"
        try:
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", artifact.get("digest") or ""):
                raise RuntimeError("Missing API SHA256; no download or deletion")
            if not path.exists():
                download(artifact, path)
            record["verification"] = verify(path, artifact)
            record.pop("error", None)
            save(manifest_path, manifest)
            current = api(f"{REPO}/actions/artifacts/{key}", missing_ok=True)
            if current is not None:
                for field in ("id", "name", "size_in_bytes", "digest", "workflow_run"):
                    if current.get(field) != artifact.get(field):
                        raise RuntimeError(f"Remote metadata changed: {field}")
                if not eligible(current):
                    raise RuntimeError("Remote no longer eligible")
                record["delete_requested_at"] = now()
                save(manifest_path, manifest)
                api(f"{REPO}/actions/artifacts/{key}", method="DELETE")
                record["delete_succeeded_at"] = now()
                save(manifest_path, manifest)
            if api(f"{REPO}/actions/artifacts/{key}", missing_ok=True) is not None:
                raise RuntimeError("Artifact still present after DELETE")
            record["absence_http_status"] = 404
            record["absence_checked_at"] = now()
            save(manifest_path, manifest)
            print(json.dumps({"id": artifact["id"], "name": artifact["name"],
                              "bytes": record["verification"]["zip_bytes"],
                              "sha256": record["verification"]["zip_sha256"],
                              "deleted": True, "absence": 404}), flush=True)
        except Exception as error:
            # Avoid logging signed download URLs or subprocess stderr.
            record["error"] = str(error) if isinstance(error, RuntimeError) else type(error).__name__
            record["error_at"] = now()
            save(manifest_path, manifest)
            print(json.dumps({"id": artifact["id"], "error": record["error"]}), flush=True)
            break


def audit(before):
    after = inventory()
    save(ROOT / "inventory-after.json", after)
    release_after = release()
    save(ROOT / "release-after.json", release_after)
    baseline = json.loads((ROOT / "release-before.json").read_text(encoding="utf-8"))
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"records": {}}
    records = list(manifest["records"].values())
    deleted = [r for r in records if r.get("delete_succeeded_at") and r.get("absence_http_status") == 404]
    verified = [r for r in records if r.get("verification")]
    remaining = {a["id"] for a in after["artifacts"]}
    protected = [a for a in before["artifacts"] if not eligible(a)]
    local_checks = []
    for record in verified:
        proof = verify(Path(record["verification"]["path"]), record["artifact"])
        local_checks.append({"id": record["artifact"]["id"], **proof})
    save(ROOT / "local-final-verification.json", local_checks)
    report = {"at": now(), "verified_zip_count": len(verified),
              "verified_zip_bytes": sum(r["verification"]["zip_bytes"] for r in verified),
              "deleted_count": len(deleted),
              "deleted_bytes": sum(r["artifact"]["size_in_bytes"] for r in deleted),
              "remaining_artifact_count": len(after["artifacts"]),
              "remaining_image_count": sum(a["name"].startswith("resense-image-") for a in after["artifacts"]),
              "remaining_image_bytes": sum(a["size_in_bytes"] for a in after["artifacts"] if a["name"].startswith("resense-image-")),
              "protected_original_count": len(protected),
              "protected_missing_ids": [a["id"] for a in protected if a["id"] not in remaining],
              "release_v1_0_0_unchanged": baseline == release_after,
              "disk_free_bytes": shutil.disk_usage(ROOT).free,
              "reserve_bytes": RESERVE,
              "errors": [{"id": r["artifact"]["id"], "error": r["error"]} for r in records if r.get("error")],
              "quota_note": "Deletion verified; quota availability not verified. GitHub recalculation may take 6-12 hours."}
    save(ROOT / "summary.json", report)
    print(json.dumps(report), flush=True)


def export_evidence():
    destination = ROOT.parent / "rs-integration-20261016" / "docs" / "evidence" / "integration_ci_2026-10-16" / "artifact_retention"
    if not destination.parent.is_dir():
        raise RuntimeError("Expected integration evidence parent is missing")
    destination.mkdir(exist_ok=True)
    outputs = []
    for name in ("manifest.json", "summary.json", "preflight.json", "release-before.json",
                 "release-after.json", "local-final-verification.json", "retain_artifacts.py"):
        target = destination / name
        shutil.copyfile(ROOT / name, target)
        outputs.append(target)
    for name in ("inventory-before.json", "inventory-after.json"):
        data = json.loads((ROOT / name).read_text(encoding="utf-8"))
        compact = {"at": data["at"], "count": len(data["artifacts"]),
                   "page_counts": [len(page["artifacts"]) for page in data["pages"]],
                   "full_external_snapshot_sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
                   "artifacts": [{key: artifact.get(key) for key in
                                  ("id", "name", "size_in_bytes", "digest", "created_at", "expired", "workflow_run")}
                                 for artifact in data["artifacts"]]}
        target = destination / name
        save(target, compact)
        outputs.append(target)
    checksums = "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
                        for path in sorted(outputs))
    (destination / "SHA256SUMS").write_text(checksums, encoding="utf-8", newline="\n")
    print(json.dumps({"evidence": str(destination), "files": len(outputs) + 1,
                      "bytes": sum(path.stat().st_size for path in outputs)}), flush=True)


def main():
    if ROOT != APPROVED_ROOT:
        sys.exit("Run the helper only from the approved external archive root")
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("plan", "execute", "audit", "export"))
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()
    before, candidates = snapshot()
    if args.mode == "execute":
        execute(candidates, args.limit)
    if args.mode != "plan":
        audit(before)
    if args.mode == "export":
        export_evidence()


if __name__ == "__main__":
    main()
