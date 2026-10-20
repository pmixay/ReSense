#!/usr/bin/env python3
"""Author X3 on dirty source: original workers/metrics, explicit byte identities.

The standing release driver requires committed source. This author adapter
replaces only that identity receipt with hashes and checks them before/after;
it does not alter the probe, detector, transforms, seeds or acceptance limits.
It is not a committed-source release acceptance run.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys

from run_check import sources

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import robustness_battery as rb  # noqa: E402


def byte_identity(repo):
    import resense
    from resense import _native
    assert Path(resense.__file__).resolve().parent == repo / "resense"
    assert _native.enabled(), _native.status()
    return {"repo": str(repo), "commit": rb.git(repo, "rev-parse", "HEAD"),
            "source_sha256": sources(repo), "native": _native.status(), "author_dirty_source": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--reference", type=Path, required=True)
    a = ap.parse_args()
    cache = Path("/tmp/opencode/resense-b4-data/decoded")
    reference = rb.read_json(a.reference)
    rb.validated_entries(reference, cache, ROOT)
    inputs = {b: rb.source_info(cache / b, n) for b, n in rb.BAGS.items()}
    for b, info in inputs.items():
        assert {k: v for k, v in info.items() if k != "path"} == {
            k: v for k, v in reference["sources"][b].items() if k != "path"}
    before = byte_identity(ROOT)
    assert rb.protocol() == reference["protocol"]
    raw = a.out.with_suffix(".raw")
    raw.mkdir()
    jobs = []
    for bag in rb.BAGS:
        for variant, args in rb.VARIANTS.items():
            folder = raw / bag / variant
            folder.mkdir(parents=True)
            job = {"repo": str(ROOT), "cache": str(cache / bag), "prefix": str(folder / "probe"),
                   "args": args, "seed": int(variant[-1]) if variant.startswith("drop30_s") else 7}
            plan = folder / "job.json"
            rb.write_new(plan, job)
            jobs.append((f"{bag}/{variant}", plan, job))

    def run(item):
        key, plan, job = item
        with (plan.parent / "process.log").open("x") as log:
            result = subprocess.run([sys.executable, __file__, "--worker", str(plan)], cwd=ROOT,
                env=rb.environment(ROOT, None), stdout=log, stderr=subprocess.STDOUT)
        assert result.returncode == 0, (key, result.returncode)
        bag, variant = key.split("/")
        meta, _ = rb.cache_meta(cache / bag, rb.BAGS[bag])
        path = Path(job["prefix"] + ".jsonl")
        assert rb.read_json(job["prefix"] + ".complete.json")["identity"] == before
        rows = rb.checked_rows(path, meta, 2 if variant == "hz5" else 1)
        labels = rb.read_json(ROOT / f"labels/{bag}.json") if bag in reference["labels"] else None
        metrics = rb.summarize(rows, labels)
        comparison = rb.compare_metrics(reference["entries"][key]["metrics"], metrics)
        print(key, metrics["stop_frames"], metrics["stop_episodes"],
              all(r["passed"] for r in comparison), flush=True)
        return key, {"metrics": metrics, "comparison": comparison, "raw_path": str(path), "raw_sha256": rb.sha256(path)}

    with ThreadPoolExecutor(max_workers=2) as pool:
        entries = dict(pool.map(run, jobs))
    assert byte_identity(ROOT) == before
    report = {"kind": "author-X3-dirty-byte-identified", "evaluation": before, "sources": inputs,
              "reference": str(a.reference), "reference_sha256": rb.sha256(a.reference),
              "protocol": rb.protocol(), "entries": entries,
              "passed": all(r["passed"] for e in entries.values() for r in e["comparison"])}
    rb.write_new(a.out, report)
    return int(not report["passed"])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        rb.identity = byte_identity
        rb.worker(sys.argv[2])
    else:
        raise SystemExit(main())
