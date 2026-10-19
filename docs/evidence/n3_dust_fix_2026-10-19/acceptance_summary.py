#!/usr/bin/env python3
"""Re-derive the N3 acceptance numbers from raw battery rows (independent of the battery's own
counters): decisions/episodes from each row's STOP flag, degraded state from health, and object
STOP rows with an independently written greedy association (same tolerances as resense.metrics:
|d - d_gt| <= max(2, 0.03 d_gt) + 0.5 * length, |lateral - lat_gt| <= 1.0 m), then cross-checked
against the battery's own summary counters (any disagreement is listed).

    acceptance_summary.py --on <battery-on work> --off <battery-off work> --ref <battery-ref work>
        --labels <labels dir> --out acceptance.json
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

EMPTY = ["doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
         "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch"]
LEVELS = ["clean", "low", "medium", "high"]
DUST_MSG = "diffuse volumetric returns"


def rows(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(l) for l in f]


def find(root, bag, level):
    hits = sorted(Path(root).rglob(f"{bag}_{level}.jsonl.gz"))
    assert len(hits) == 1, (root, bag, level, hits)
    return hits[0]


def summaries(root):
    out = {}
    for s in Path(root).rglob("summary.json"):
        for bag, rec in json.loads(s.read_text())["recordings"].items():
            out[bag] = rec["levels"]
    return out


def match(det, lab):
    tol = max(2.0, 0.03 * lab["distance"]) + 0.5 * max(lab["size"][0], 0.0)
    return abs(det["distance"] - lab["distance"]) <= tol and abs(det["lateral"] - lab["lateral"]) <= 1.0


def assign(dets, labs):
    """Greedy one-to-one on the smallest normalized error (independent of the battery's solver)."""
    pairs = []
    for gi, lab in enumerate(labs):
        tol = max(2.0, 0.03 * lab["distance"]) + 0.5 * max(lab["size"][0], 0.0)
        for di, d in enumerate(dets):
            if match(d, lab):
                pairs.append((abs(d["distance"] - lab["distance"]) / tol + abs(d["lateral"] - lab["lateral"]), gi, di))
    used_g, used_d, out = set(), set(), {}
    for _, gi, di in sorted(pairs):
        if gi not in used_g and di not in used_d:
            used_g.add(gi); used_d.add(di); out[gi] = di
    return out


def analyse(rs, labels):
    stop = [bool(r["obstacle"]) for r in rs]
    episodes = sum(1 for i, s in enumerate(stop) if s and (i == 0 or not stop[i - 1]))
    dec = {}
    silent_go = degraded = guard_degraded = guard_clear_nonzero = 0
    for r in rs:
        h = r.get("health") or {}
        dl = h.get("decision_level", h.get("level"))
        word = "STOP" if r["obstacle"] else "FAULT" if h.get("level") == "error" else (
            "CAUTION" if r["warning"] or dl == "warn" else "GO")
        assert word == r["decision"], (r["frame"], word, r["decision"])
        dec[word] = dec.get(word, 0) + 1
        deg = dl in ("warn", "error")
        degraded += deg
        silent_go += word == "GO" and not deg
        if any(DUST_MSG in m for m in h.get("messages", [])):
            guard_degraded += 1
            guard_clear_nonzero += (r.get("clear_distance") or 0) != 0 or (h.get("monitored_range") or 0) != 0
    objects = {}
    for r in rs:
        labs = [l for l in labels.get(f"{r['frame']:05d}", []) if l.get("n_points", 1) > 0 and l.get("plausible", True)]
        a = assign(r.get("detections", []), labs)
        for gi, lab in enumerate(labs):
            if not lab.get("in_gauge", True):
                continue
            o = objects.setdefault(lab.get("label", "obstacle"), {"inside": 0, "stop_frames": [], "first_stop_m": None})
            o["inside"] += 1
            if gi in a:
                o["stop_frames"].append(r["frame"])
                if o["first_stop_m"] is None:
                    o["first_stop_m"] = float(lab["distance"])
    return {"frames": len(rs), "stop_frames": sum(stop), "episodes": episodes, "decisions": dec,
            "degraded": degraded, "silent_go": silent_go, "guard_degraded": guard_degraded,
            "guard_degraded_with_range": guard_clear_nonzero, "objects": objects}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--on", type=Path, required=True)
    ap.add_argument("--off", type=Path)
    ap.add_argument("--ref", type=Path)
    ap.add_argument("--labels", type=Path, required=True)
    ap.add_argument("--bags", default=",".join(EMPTY + ["doubleT_obstacle", "cloud_with_fake_obj"]))
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    result = {"runs": {}, "cross_check_disagreements": []}
    for name, root in (("on", a.on), ("off", a.off), ("ref", a.ref)):
        if root is None:
            continue
        sums = summaries(root)
        run = {}
        for bag in a.bags.split(","):
            lp = a.labels / f"{bag}.json"
            labels = json.loads(lp.read_text()) if lp.exists() else {}
            run[bag] = {}
            for level in LEVELS:
                p = find(root, bag, level)
                m = analyse(rows(p), labels)
                run[bag][level] = m
                s = sums[bag][level]
                if s.get("stop_episodes", 0) != m["episodes"] or s.get("STOP", 0) != m["stop_frames"] \
                        or s.get("degraded_frames", 0) != m["degraded"]:
                    result["cross_check_disagreements"].append([name, bag, level, "counts"])
                for obj, o in s.get("objects", {}).items():
                    mine = m["objects"].get(obj, {"stop_frames": [], "inside": 0})
                    if sorted(o["stop_frames"]) != mine["stop_frames"] or o["visible_inside_frames"] != mine["inside"]:
                        result["cross_check_disagreements"].append([name, bag, level, obj,
                                                                    len(o["stop_frames"]), len(mine["stop_frames"])])
        result["runs"][name] = run
    on = result["runs"]["on"]
    crit = {"1_empty": {}, "2_low": {}, "3_no_silent_go": {}}
    for bag in EMPTY:
        if bag not in on:
            continue
        clean = on[bag]["clean"]["episodes"]
        for level in ("low", "medium", "high"):
            e = on[bag][level]["episodes"]
            crit["1_empty"][f"{bag}/{level}"] = {"clean": clean, "episodes": e, "pass": e <= clean + 1}
    if "doubleT_obstacle" in on:
        c, l = on["doubleT_obstacle"]["clean"]["objects"], on["doubleT_obstacle"]["low"]["objects"]
        for obj in c:
            lost = sorted(set(c[obj]["stop_frames"]) - set(l.get(obj, {}).get("stop_frames", [])))
            first_c, first_l = c[obj]["first_stop_m"], l.get(obj, {}).get("first_stop_m")
            crit["2_low"][obj] = {"clean_rows": len(c[obj]["stop_frames"]), "low_rows": len(l.get(obj, {}).get("stop_frames", [])),
                                  "lost_rows": lost, "first_clean_m": first_c, "first_low_m": first_l,
                                  "first_ratio": None if not (first_c and first_l) else first_l / first_c,
                                  "pass": not lost and bool(first_c and first_l and first_l >= 0.9 * first_c)}
    for bag in on:
        for level in ("medium", "high"):
            m = on[bag][level]
            crit["3_no_silent_go"][f"{bag}/{level}"] = {"silent_go": m["silent_go"], "guard_degraded": m["guard_degraded"],
                                                        "frames": m["frames"], "with_range": m["guard_degraded_with_range"],
                                                        "pass": m["silent_go"] == 0 and m["guard_degraded_with_range"] == 0}
    result["criteria"] = crit
    a.out.write_text(json.dumps(result, indent=1) + "\n")
    for k, v in crit.items():
        print(k, sum(x["pass"] for x in v.values()), "/", len(v), "pass")
    print("cross-check disagreements:", len(result["cross_check_disagreements"]))


if __name__ == "__main__":
    main()
