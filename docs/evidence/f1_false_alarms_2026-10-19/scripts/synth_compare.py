#!/usr/bin/env python3
"""Synthetic bags: switches at 0 (``off``) vs the candidate (``cand``), both from synth_local.py. Per bag: decision
counts and per-frame transitions (each lowered decision listed with the labelled objects of that frame); per
labelled object (N5 team labels, ``scripts/score_team_labels.score``): STOP-matched frames (bounds), first STOP
distance, warning-matched frames. P1's background false-STOP frames (19.10, organizers' markers) are flagged.
``synth_compare.py PREFIX`` (reads PREFIX_{off,cand}_<bag>.jsonl)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.score_team_labels import score  # noqa: E402

LABELS = ROOT / "docs/evidence/n5_labels_2026-10-17"
BACKGROUND = {"synthetic_switch": set(range(7, 15)), "synthetic_tunnels": {147, 148, 149, 367}, "synthetic_platform": set()}
RANK = {"GO": 0, "CAUTION": 1, "FAULT": 1, "STOP": 2}
prefix = sys.argv[1]
out = {}
for bag in ("synthetic_platform", "synthetic_switch", "synthetic_tunnels"):
    labels = json.loads((LABELS / f"labels_{bag}.json").read_text())
    runs = {k: [json.loads(x) for x in open(f"{prefix}_{k}_{bag}.jsonl")] for k in ("off", "cand")}
    sc = {k: score(v, labels) for k, v in runs.items()}
    trans, lowered = {}, []
    for a, b in zip(runs["off"], runs["cand"]):
        if a["decision"] != b["decision"]:
            k = f'{a["decision"]}->{b["decision"]}'
            trans[k] = trans.get(k, 0) + 1
            if RANK[b["decision"]] < RANK[a["decision"]]:
                objs = [o["name"] for o in labels[f'{a["i"]:05d}'] if o.get("n_points", 0) > 0]
                lowered.append({"frame": a["i"], "off": a["decision"], "cand": b["decision"], "labelled_objects": objs,
                                "p1_background": a["i"] in BACKGROUND[bag],
                                "off_dets": [(d["d"], d["lat"], d["kind"], d["reason"]) for d in a["dets"]]})
    objects = {}
    for name in sc["off"]["objects"]:
        o, c = sc["off"]["objects"][name], sc["cand"]["objects"][name]
        objects[name] = {k: [o[k], c[k]] for k in ("stop_match_frames_bounds", "first_stop_m_certain_assignment",
                                                    "first_stop_m_possible_assignment", "certain_inside_stop_frames_bounds",
                                                    "warning_match_frames_bounds")}
    bg = {k: sorted(f for f in BACKGROUND[bag] if runs[k][f]["decision"] == "STOP") for k in ("off", "cand")}
    out[bag] = {"decisions": {k: sc[k]["decisions"] for k in sc}, "transitions": trans, "lowered": lowered,
                "objects": objects, "p1_background_stop_frames": bg,
                "unmatched_stop_detections": {k: sc[k]["summary"]["unmatched_stop_detections"] for k in sc}}
print(json.dumps(out, indent=1))
