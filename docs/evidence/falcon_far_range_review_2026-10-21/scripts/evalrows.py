#!/usr/bin/env python3
"""Reviewer's evaluation of replay rows (independent of falcon_eval.py; same reviewed person anchors, own code).

A STOP detection belongs to a target when its centre in the raw frame (c @ mount_rotation; the falcon_ros axes are
the ROS axes) lies within 2.5 m along and 1.0 m laterally of the target's position in that frame. Targets: the main
person and the early walker (N2 reviewed anchors, box centre, interpolated over gaps <= 25 frames), plus injected
targets of a scene spec; all moved by the scene's warp / scroll when their group (centre) is edited.

Per run: decisions, STOP episodes, episodes with no target-associated STOP detection ("false episodes"), STOP frames
with at least one unassociated STOP detection (per detection, stricter than falcon_eval's frame credit), per target
first STOP (frame, raw along) and STOP frames.

    evalrows.py rows.jsonl [--spec spec.json] [--frames a:b] [--json out.json]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/ReSense/docs/evidence/n2_falcon_2026-10-18")
import summarize_falcon as N2  # noqa: E402

TRACK = json.loads(Path("/home/user/ReSense/docs/evidence/falcon_long_range_2026-10-19/track_reference.json").read_text())["track"]
_, BY = N2.references()


def arc(x, xc, R):
    return 0.5 * (x - xc) ** 2 / R if x > xc else 0.0


def moved(x, y, k, spec):
    """Apply the scene edit of window frame k to a centre-group point (x, y) (raw)."""
    sc = spec.get("scroll")
    sx = float(sc["v"]) * 0.1 * k if sc else 0.0
    if sc and x > sc.get("x_from", 50.0):
        x -= sx
    for w in spec.get("warp", []):
        if "centre" in w["groups"]:
            y += float(w.get("dir", 1.0)) * arc(x, float(w["xc"]) - sx, float(w["R"]))
    return x, y


def targets(i, k, spec, injected):
    out = []
    if not spec.get("scroll") or spec["scroll"].get("base_frame") is None:
        for ep, box in BY.get(i, {}).items():
            c = np.asarray(box).mean(axis=0)
            out.append((ep, *moved(float(c[0]), float(c[1]), k, spec)))
    for n, t in enumerate(injected):
        if not (int(t["from"]) <= i < int(t["to"])):
            continue
        if "path" in t:
            P = np.asarray(t["path"], dtype=float)
            x, lat = float(np.interp(i, P[:, 0], P[:, 1])), float(np.interp(i, P[:, 0], P[:, 2]))
        elif "dist" in t:
            x, lat = float(t["dist"]), float(t.get("lat", 0.0))
        else:
            x = max(float(t["start"]) - float(t["speed"]) * 0.1 * (i - int(t["from"])), float(t.get("stop_at", 0.0)))
            lat = float(t.get("lat", 0.0))
        y = lat + TRACK["a"] + TRACK["b"] * x
        out.append((t.get("name", f"inj{n}"), *moved(x, y, k, spec)))
    return out


def evaluate(rows, spec=None, lo=None):
    spec = spec or {}
    injected = spec.get("inject", {}).get("targets", [])
    lo = rows[0]["i"] if lo is None else lo
    eps, cur = [], None
    per = {}
    bad_frames = []
    dec = {}
    for r in rows:
        dec[r["decision"]] = dec.get(r["decision"], 0) + 1
        tg = targets(r["i"], r["i"] - lo, spec, injected)
        R = np.asarray(r["mount_rotation"])
        hit_any, unassoc = set(), False
        for d in r["dets"]:
            c = np.asarray(d["c"]) @ R
            m = [n for n, x, y in tg if abs(c[0] - x) < 2.5 and abs(c[1] - y) < 1.0]
            if m:
                hit_any.update(m)
            else:
                unassoc = True
        for n, x, y in tg:
            p = per.setdefault(n, {"stop_frames": 0, "first_stop_frame": None, "first_stop_x": None})
            p["present"] = p.get("present", 0) + 1
            if r["decision"] == "GO" and r["monitored"] is not None and x <= min(r["clear"], r["monitored"]):
                p["go_inside_clear"] = p.get("go_inside_clear", 0) + 1
        for n in hit_any:
            p = per.setdefault(n, {"stop_frames": 0, "first_stop_frame": None, "first_stop_x": None})
            p["stop_frames"] += 1
            p.setdefault("stop_list", []).append(r["i"])
            if p["first_stop_frame"] is None:
                p["first_stop_frame"] = r["i"]
                p["first_stop_x"] = round(next(x for nn, x, y in tg if nn == n), 1)
        if r["decision"] == "STOP":
            if unassoc:
                bad_frames.append(r["i"])
            cur = cur if cur is not None else {"frames": [], "assoc": False}
            cur["frames"].append(r["i"])
            cur["assoc"] |= bool(hit_any)
        elif cur is not None:
            eps.append(cur)
            cur = None
    if cur is not None:
        eps.append(cur)
    for n, p in per.items():
        # held STOP: the first STOP frame from which the target is STOPped in >= 90 % of the next 30 frames (3 s)
        st = set(p.get("stop_list", []))
        xs = {r["i"]: x for r in rows for nn, x, _ in targets(r["i"], r["i"] - lo, spec, injected) if nn == n}
        held = next((i for i in sorted(st) if sum((j in st) for j in range(i, i + 30)) >= 27), None)
        p["held_stop_frame"] = held
        p["held_stop_x"] = None if held is None else round(xs[held], 1)
        p["stop_list"] = sorted(st)
    false_eps = [[e["frames"][0], e["frames"][-1]] for e in eps if not e["assoc"]]
    return {"frames": len(rows), "decisions": dec, "stop_episodes": len(eps), "false_episodes": len(false_eps),
            "false_episode_frames": false_eps, "stop_frames_with_unassociated_det": len(bad_frames),
            "unassociated_frames": bad_frames[:60], "targets": per,
            "max_far_valid": max([r["far"]["valid"] for r in rows if r.get("far")], default=None),
            "far_frames": sum(1 for r in rows if r.get("far"))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rows")
    ap.add_argument("--spec", default="")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    rows = [json.loads(line) for line in open(a.rows)]
    spec = json.loads(Path(a.spec).read_text()) if a.spec else {}
    res = evaluate(rows, spec)
    print(json.dumps({k: v for k, v in res.items() if k != "unassociated_frames"}))
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
