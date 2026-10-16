#!/usr/bin/env python3
"""Build the X1 cause tables from the two attribution runs (run_x1.sh output).

    make_report.py <x1 root> <out dir>      # <x1 root>/<tag>/<case>.attrib.json, .off.json / .off.jsonl

Writes <out dir>/x1_summary.json (judge summaries, BACKLOG anchors, hooks-off proofs, per case and
version: cause -> frames per distance bin, frame-level cause changes 707ea9c -> 1.1.0) and
<out dir>/x1_tables.md. Exit 1 if any row is unclassified / unmapped or a hooks-off proof failed.
"""
import collections
import hashlib
import json
from pathlib import Path
import sys

TAGS = ("707ea9c", "1.1.0")
BINS = [(3, 30), (30, 60), (60, 100), (100, 150), (150, 200), (200, 260)]
ANCHORS = {"A_cube05": {"first_stop_X": 135.06, "held_from_X": 83.37, "stop_frames": 66},
           "S_person_100": {"stop_frames": 82}}


def bin_of(x):
    return next((f"{lo}-{hi}" for lo, hi in BINS if lo <= x < hi), "other")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(root, out_dir):
    root, out_dir = Path(root), Path(out_dir)
    cases = sorted({p.name[:-len(".attrib.json")] for p in (root / TAGS[0]).glob("*.attrib.json")})
    summary = {"cases": {}, "anchors": {}, "errors": [], "totals": {}}
    totals = {t: collections.Counter() for t in TAGS}
    for case in cases:
        entry = {}
        for tag in TAGS:
            rep = json.loads((root / tag / f"{case}.attrib.json").read_text())
            if not rep.get("hooks_off", {}).get("equal"):
                summary["errors"].append(f"{tag}/{case}: hooks-off proof missing or failed")
            causes = collections.defaultdict(collections.Counter)
            for r in rep["rows"]:
                if r["hit"]:
                    continue
                causes[r["cause"]][bin_of(r["X"])] += 1
                totals[tag][r["cause"]] += 1
                if r["cause"].startswith(("unclassified", "unmapped")):
                    summary["errors"].append(f"{tag}/{case}: frame {r['k']} {r['cause']}")
            judge = None
            off = root / tag / f"{case}.off.json"
            if off.exists():
                judge = json.loads(off.read_text())["summary"]
            e = {"commit": rep["commit"], "version": rep["version"], "visible": len(rep["rows"]),
                 "stop_hits": sum(r["hit"] for r in rep["rows"]),
                 "causes": {c: dict(v) for c, v in sorted(causes.items(), key=lambda kv: -sum(kv[1].values()))},
                 "attrib_sha256": sha(root / tag / f"{case}.attrib.json"), "hooks_off": rep.get("hooks_off")}
            if judge:
                e["judge_summary"] = {k: judge[k] for k in ("first_visible_X", "first_stop_X", "held_from_X",
                                                            "visible_frames", "stop_frames", "bins")}
            entry[tag] = e
        a, b = (json.loads((root / t / f"{case}.attrib.json").read_text())["rows"] for t in TAGS)
        a, b = ({r["k"]: r for r in rows} for rows in (a, b))   # placement follows each version's track model
        changed = [{"k": k, "X": (a.get(k) or b.get(k))["X"],
                    **{t: (rows[k].get("cause", "STOP") if k in rows else "not_visible") for t, rows in zip(TAGS, (a, b))}}
                   for k in sorted(set(a) | set(b))
                   if (a[k].get("cause", "STOP") if k in a else None) != (b[k].get("cause", "STOP") if k in b else None)]
        entry["changed_rows"] = changed
        summary["cases"][case] = entry
        if case in ANCHORS:
            got = entry[TAGS[0]].get("judge_summary", {})
            summary["anchors"][case] = {"expected": ANCHORS[case],
                                        "actual_707ea9c": {k: got.get(k) for k in ANCHORS[case]},
                                        "equal": all(got.get(k) == v for k, v in ANCHORS[case].items())}
    summary["totals"] = {t: dict(totals[t].most_common()) for t in TAGS}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "x1_summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    md = ["| case | version | visible | STOP hits | non-STOP | causes (frames) |", "|---|---|---:|---:|---:|---|"]
    for case, entry in summary["cases"].items():
        for tag in TAGS:
            e = entry[tag]
            cs = ", ".join(f"{c} {sum(v.values())}" for c, v in e["causes"].items())
            md.append(f"| {case} | {tag} | {e['visible']} | {e['stop_hits']} | {e['visible'] - e['stop_hits']} | {cs} |")
    md += ["", "Cause → non-STOP visible frames per distance bin (m), all cases, " + TAGS[1] + ":", "",
           "| cause | " + " | ".join(f"{lo}–{hi}" for lo, hi in BINS) + " | total |",
           "|---|" + "---:|" * (len(BINS) + 1)]
    agg = collections.defaultdict(collections.Counter)
    for entry in summary["cases"].values():
        for c, v in entry[TAGS[1]]["causes"].items():
            agg[c].update(v)
    for c, v in sorted(agg.items(), key=lambda kv: -sum(kv[1].values())):
        md.append(f"| {c} | " + " | ".join(str(v.get(f"{lo}-{hi}", 0)) for lo, hi in BINS) + f" | {sum(v.values())} |")
    (out_dir / "x1_tables.md").write_text("\n".join(md) + "\n")
    print("errors:", len(summary["errors"]), "anchors:", {k: v["equal"] for k, v in summary["anchors"].items()})
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
