#!/usr/bin/env python3
"""Compare paired set F runs, excluding skipped sequences from both denominators.

    python scripts/compare_setf.py out/legacy.json out/anchored.json --out out/paired.json

The per-mode summaries include every *attempted* sequence, so their first-detection medians
must not be compared when an anchored run skips an unreliable trajectory. This tool checks
the experiment configuration, object sampling and frame alignment before comparing hits.
"""
from __future__ import annotations

import argparse
import json
import statistics

BINS = ((0, 50), (50, 100), (100, 150), (150, 200), (200, 250))


def compare(legacy: dict, anchored: dict) -> dict:
    for key in ("schema", "source"):
        if legacy.get(key) != anchored.get(key):
            raise ValueError(f"different {key}")
    if legacy.get("schema") != "setF-placement-v1":
        raise ValueError("expected setF-placement-v1 reports")
    lp, ap = legacy["parameters"], anchored["parameters"]
    if lp["placement_mode"] != "legacy" or ap["placement_mode"] != "anchored":
        raise ValueError("expected legacy first, anchored second")
    for key in ("place", "seed", "files", "frames", "kinds", "start_m", "lateral_range",
                "given_speed", "far_min_height", "config_sha256", "speeds_sha256",
                "selected_stamps_sha256", "cache_files"):
        if lp.get(key) != ap.get(key):
            raise ValueError(f"different {key}: cannot compare unpaired experiments")
    aseq, bseq = legacy["sequences"], anchored["sequences"]
    if len(aseq) != len(bseq):
        raise ValueError("different number of sequences")
    pairs = []
    for old, new in zip(aseq, bseq):
        for key in ("file0", "kind", "d0", "lateral", "refl"):
            if old[key] != new[key]:
                raise ValueError(f"different sampled {key}: cannot pair {old['file0']} and {new['file0']}")
        if old.get("skipped") or new.get("skipped"):
            pairs.append({"file0": old["file0"], "kind": old["kind"],
                          "skipped": {"legacy": old.get("skipped"), "anchored": new.get("skipped")}})
            continue
        if [r["frame"] for r in old["rows"]] != [r["frame"] for r in new["rows"]]:
            raise ValueError(f"different frame selection for {old['file0']}")
        rows = list(zip(old["rows"], new["rows"]))
        differences = [abs(float(b["gt_vehicle_y_m"]) - float(a["gt_vehicle_y_m"])) for a, b in rows]
        by_range = {mode: {f"{lo}-{hi}": [sum(r["hit"] and r["n"] > 0 for r in selected
                                                  if lo <= r["d"] < hi),
                                             sum(r["n"] > 0 for r in selected if lo <= r["d"] < hi)]
                           for lo, hi in BINS}
                    for mode, selected in (("legacy", old["rows"]), ("anchored", new["rows"]))}
        pairs.append({"file0": old["file0"], "kind": old["kind"], "frames": len(rows),
                      "first_m": {"legacy": old["first"], "anchored": new["first"]},
                      "visible": {"legacy": sum(a["n"] > 0 for a, _ in rows),
                                  "anchored": sum(b["n"] > 0 for _, b in rows)},
                      "visible_hits": {"legacy": sum(a["n"] > 0 and a["hit"] for a, _ in rows),
                                       "anchored": sum(b["n"] > 0 and b["hit"] for _, b in rows)},
                      "recall_by_bin": by_range,
                      "legacy_only_hits": sum(a["n"] > 0 and a["hit"] and not b["hit"] for a, b in rows),
                      "anchored_only_hits": sum(b["n"] > 0 and b["hit"] and not a["hit"] for a, b in rows),
                      "max_axis_delta_m": round(max(differences), 2) if differences else None,
                      "median_axis_delta_m": round(statistics.median(differences), 2) if differences else None})
    per_kind = {}
    for kind in sorted({p["kind"] for p in pairs}):
        attempted = [p for p in pairs if p["kind"] == kind and "skipped" not in p]
        per_kind[kind] = {"paired_sequences": len(attempted),
                          "skipped": sum(p["kind"] == kind and "skipped" in p for p in pairs),
                          "visible": {mode: sum(p["visible"][mode] for p in attempted)
                                      for mode in ("legacy", "anchored")},
                          "visible_hits": {mode: sum(p["visible_hits"][mode] for p in attempted)
                                           for mode in ("legacy", "anchored")},
                          "recall_by_bin": {mode: {label: [sum(p["recall_by_bin"][mode][label][i]
                                                              for p in attempted) for i in (0, 1)]
                                                         for label in (f"{lo}-{hi}" for lo, hi in BINS)}
                                            for mode in ("legacy", "anchored")},
                          "first_median": {mode: round(statistics.median(
                              p["first_m"][mode] for p in attempted if p["first_m"][mode] is not None), 1)
                              if any(p["first_m"][mode] is not None for p in attempted) else None
                              for mode in ("legacy", "anchored")}}
    return {"source": "paired synthetic positives on organizer empty-ride frames",
            "parameters": {k: lp.get(k) for k in ("files", "frames", "kinds", "seed", "start_m",
                                                  "lateral_range", "config_sha256", "speeds_sha256",
                                                  "selected_stamps_sha256")},
            "per_kind": per_kind, "sequences": pairs}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("legacy")
    p.add_argument("anchored")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    with open(args.legacy, encoding="utf-8") as fh:
        old = json.load(fh)
    with open(args.anchored, encoding="utf-8") as fh:
        new = json.load(fh)
    result = compare(old, new)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)
    print(json.dumps(result["per_kind"], indent=1))


if __name__ == "__main__":
    main()
