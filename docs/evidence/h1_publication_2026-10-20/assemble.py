"""Copy explicit H1 evidence allowlists and record live input metadata on the VM."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.parse
import urllib.request


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def git(repo, *args):
    return subprocess.check_output(
        ["git", "--no-optional-locks", "-C", str(repo), *args], text=True
    ).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    source, repo = args.source.resolve(), args.repo.resolve()
    assert source != repo and (repo / "docs/evidence").is_dir()
    summary = repo / "docs/evidence/h1_publication_2026-10-20"
    summary.mkdir(exist_ok=True)
    paths, copied = [], []
    packages = {
        "h1_independent_2026-10-20": ["README.md", "review_reference.py", "report.json"],
        "h1_final_review_2026-10-20": [
            "README.md", "review_h1.py", "report.json", "crosscheck.py",
            "crosscheck.json", "SHA256SUMS",
        ],
    }
    for name in ["h1_miss_audit_2026-10-20", "h1_rail_limits_2026-10-20"]:
        manifest = json.loads((source / "docs/evidence" / name / "publication-manifest.json").read_text())
        if "exact_allowlist" in manifest:
            packages[name] = manifest["exact_allowlist"]
        else:
            packages[name] = sorted(set(manifest["payload_files"]) | set(manifest["metadata_files"]))
    for name, names in packages.items():
        dest = repo / "docs/evidence" / name
        dest.mkdir()
        for name_only in names:
            relative = Path(name_only)
            assert not relative.is_absolute() and ".." not in relative.parts
            src = source / "docs/evidence" / name / relative
            target = dest / relative
            assert src.is_file() and src.stat().st_size < 20_000_000
            target.parent.mkdir(parents=True, exist_ok=True)
            assert not target.exists()
            shutil.copy2(src, target)
            assert src.stat().st_size == target.stat().st_size and sha(src) == sha(target)
            path = str(target.relative_to(repo))
            paths.append(path)
            copied.append({"path": path, "bytes": target.stat().st_size, "sha256": sha(target)})

    urls = ["https://disk.yandex.ru/d/DK6H3Lxiyi-M-Q", "https://disk.yandex.ru/d/SfBeRHbs8bNJAQ"]
    keep = ["name", "type", "size", "sha256", "modified", "path"]
    sources = []
    for url in urls:
        api = "https://cloud-api.yandex.net/v1/disk/public/resources?" + urllib.parse.urlencode(
            {"public_key": url, "limit": 100}
        )
        with urllib.request.urlopen(api, timeout=45) as response:
            data = json.load(response)
        item = {"public_url": url, "metadata": {k: data[k] for k in keep if k in data}}
        if data["type"] == "dir":
            raw_items = data["_embedded"]["items"]
            assert data["_embedded"]["total"] == len(raw_items) == 6
            item["items"] = [{k: row[k] for k in keep if k in row} for row in raw_items]
        sources.append(item)
    falcon = sources[0]["metadata"]
    assert falcon["name"] == "falcon_test.zst" and falcon["size"] == 6758209772
    assert falcon["sha256"] == "90dea27d8636bcb2e5cdddf9bc15add3eae0e05196c2b3de959482da7e505611"
    assert next(r for r in sources[1]["items"] if r["name"] == falcon["name"])["sha256"] == falcon["sha256"]
    write_new(summary / "user-sources.json", {"sources": sources, "download_urls_excluded": True})
    head = git(repo, "rev-parse", "HEAD")
    assert head == "520e7dcd2843a0e7c9055fca6c186c0d1687945f"
    production_delta = git(repo, "diff", "--name-only", "f56ad5e..HEAD", "--", "resense", "native", "configs", "ros2_ws", "setup.py", "pyproject.toml").splitlines()
    assert production_delta == ["resense/lowobj.py"], production_delta
    write_new(summary / "copy-receipt.json", {
        "measured_original": "f56ad5e62d9d051811c804734c7731b6951eae90",
        "current_replayed_head": head,
        "production_delta": production_delta,
        "copied_files": copied,
        "copied_bytes": sum(r["bytes"] for r in copied),
        "copy_verified_by": "source/target length and SHA-256 for every allowlisted file",
    })
    for directory in [summary, repo / "docs/evidence/h1_current_source_2026-10-20"]:
        for path in directory.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.name != "publication-paths.txt":
                assert path.stat().st_size < 20_000_000
                paths.append(str(path.relative_to(repo)))
    paths.extend(["docs/BACKLOG.md", "docs/DETECTOR_FREEZE.md", "docs/evidence/README.md",
                  "docs/evidence/h1_publication_2026-10-20/publication-paths.txt"])
    with (summary / "publication-paths.txt").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(sorted(set(paths))) + "\n")
    print(json.dumps({"files_copied": len(copied), "copied_bytes": sum(r["bytes"] for r in copied),
                      "intended_git_paths": len(set(paths)), "head": head}, indent=2))


if __name__ == "__main__":
    main()
