#!/usr/bin/env python3
"""Post-filter screen of competitor ideas 1 and 5 on the sealed 1.3.0 detector's saved output.

    python screen_eval.py --feat DIR_WITH_FEATURE_JSONL --base BASELINE_GATE_JSON --out OUTDIR

Rules are fixed here, before any result is read, from docs/COMPETITOR_SURVEY_2026-10.md section 3 and the
hakatanon report; nothing is tuned.  A vetoed STOP detection is *demoted* to a CAUTION detection (never
deleted: "demote, never delete").  The filtered per-frame JSONL is scored with the regression gate's own
functions (``recording_entry`` / ``set_o_entry``), so every number is the gate's number.  The identity case
(no rule) must reproduce the baseline gate JSON exactly; if it does not the screen stops.

A post-filter is a first-order proxy (DECISIONS row 30): it cannot show what a rule changes inside the tracker.
"""
import argparse
import json
import os
import sys

REPO = os.environ.get("RESENSE_REPO", "/home/user/ReSense")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import regression_gate as rg  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
import eval_real  # noqa: E402

SIX = rg.SIX
EMPTY = rg.FIVE_EMPTY
SET_O = rg.SET_O


# ---- rules: veto(det, feat) -> bool, applied to STOP detections only -------------------------------------------
def r1a(d, f):   # idea 1, opacity: returns behind the object, beyond 60 m (hakatanon: count >= 2 and d > 60)
    return f.get("ok") and d["distance"] > 60.0 and f["behind_n"] >= 2


def r1b(d, f):   # idea 1, front lift: ground in front rises >= 0.1 m above the object's bottom, bottom < 2 m
    return (f.get("ok") and d["distance"] > 40.0 and f["low"] < 2.0 and f["front_maxh"] is not None
            and f["front_maxh"] >= f["low"] + 0.1)


def r1c(d, f):   # idea 1, attachment: outside returns within 0.35 + 0.008 d outnumber the object's own
    return f.get("ok") and d["distance"] > 40.0 and f["attach"] > 1.0


def r1(d, f):
    return r1a(d, f) or r1b(d, f) or r1c(d, f)


def r5(d, f):    # idea 5, collinearity: a 2+ m long object on a line of same-lateral, same-height returns >= 16 m long
    return f.get("ok") and d["size"][0] >= 2.0 and f["run_m"] >= 16.0


def r5_any(d, f):  # the same without the elongation requirement
    return f.get("ok") and f["run_m"] >= 16.0


def r1b_rail(d, f):   # EXPLORATORY (chosen after seeing the data): the ground in front rises above the RAIL HEAD plane
    # by >= 0.15 m, not above the object's own bottom (an object on a rail has the rail head 0.1-0.14 m above its bottom)
    return f.get("ok") and d["distance"] > 40.0 and f["front_maxh"] is not None and f["front_maxh"] >= 0.15


RULES = {"none": lambda d, f: False, "R1a_opacity": r1a, "R1b_front_lift": r1b, "R1c_attach": r1c, "R1_all": r1,
         "R5_line_elongated": r5, "R5_line_any": r5_any,
         "R1+R5": lambda d, f: r1(d, f) or r5(d, f),
         "X_R1b_rail_head": r1b_rail, "X_R1a+R1b_rail": lambda d, f: r1a(d, f) or r1b_rail(d, f)}


def load(feat_dir, bag):
    p = os.path.join(feat_dir, f"{bag}.jsonl")
    return [json.loads(line) for line in open(p, encoding="utf-8")]


def apply_rule(recs, rule):
    out, vetoed = [], []
    for r in recs:
        stop_feats = [f for f in r["feat"] if f["level"] == "stop"]
        assert len(stop_feats) == len(r["detections"]), (r["frame"], len(stop_feats), len(r["detections"]))
        keep, demote = [], []
        for det, f in zip(r["detections"], stop_feats):
            if rule(det, f):
                demote.append(det)
                vetoed.append((r["frame"], det["id"], det["distance"], det["lateral"], tuple(det["size"])))
            else:
                keep.append(det)
        r2 = {k: v for k, v in r.items() if k != "feat"}
        r2["detections"] = keep
        r2["warnings"] = list(r["warnings"]) + demote
        r2["obstacle"] = bool(keep)
        r2["warning"] = bool(r2["warnings"])
        r2["nearest_distance"] = round(min(d["distance"] for d in keep), 2) if keep else None
        out.append(r2)
    return out, vetoed


def write(recs, path):
    with open(path, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")


def score_rule(name, rule, feat_dir, outdir, cfg):
    d = os.path.join(outdir, name)
    os.makedirs(d, exist_ok=True)
    vetoed_all = {}
    for bag in SIX + [SET_O]:
        recs, v = apply_rule(load(feat_dir, bag), rule)
        write(recs, os.path.join(d, f"{bag}.jsonl"))
        vetoed_all[bag] = v
    recordings = {b: rg.recording_entry(b, [os.path.join(d, f"{b}.jsonl")], cfg,
                                        os.path.join(REPO, eval_real.LABELS[b]) if b in eval_real.LABELS else None)
                  for b in SIX}
    five = {k: sum(recordings[b][k] for b in EMPTY)
            for k in ("frames", "alarm_frames", "alarm_events", "stop_episodes", "advisory_frames")}
    set_o = rg.set_o_entry([os.path.join(d, f"{SET_O}.jsonl")], os.path.join(REPO, rg.SET_O_LABELS))
    return {"recordings": recordings, "five_empty": five, "set_O": set_o, "vetoed": vetoed_all}


def summarise(res):
    rec = res["recordings"]
    dto = rec["doubleT_obstacle"]
    so = res["set_O"]
    row = {
        "empty_STOP_frames": res["five_empty"]["alarm_frames"],
        "empty_STOP_episodes": res["five_empty"]["stop_episodes"],
        "dT_obst_hits": dto["labelled"]["hits"], "dT_obst_fp_events": dto["labelled"]["fp_events"],
        "dT_obst_per_label": dto["labelled"]["per_label"],
        "setO_inside_stop_frames": so["inside_stop_frames"],
        "setO_outside_false": so["outside_false_stop_frames"],
        "setO_bg_frames": so["background"]["alarm_frames"],
        "vetoed_rows": {b: len(v) for b, v in res["vetoed"].items() if v},
    }
    row["objects"] = {k: (o.get("stop_frames"), o.get("first_stop_m"), o.get("held_from_m"))
                      for k, o in so["objects"].items() if o.get("in_gauge")}
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feat", required=True)
    ap.add_argument("--base", required=True, help="the baseline gate JSON of the same detector on the same cache")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rules", default=",".join(RULES))
    a = ap.parse_args()
    cfg = DetectorConfig.from_dict(eval_real.load_cfg_dict(os.path.join(REPO, "configs", "default.yaml"), []))
    base = json.load(open(a.base))
    results = {}
    for name in a.rules.split(","):
        results[name] = score_rule(name, RULES[name], a.feat, a.out, cfg)
        if name == "none":
            # positive control: with no rule the filtered output must equal the gate's own numbers
            ok = True
            for b in SIX:
                for k in ("frames", "alarm_frames", "alarm_events", "stop_episodes", "advisory_frames"):
                    if results["none"]["recordings"][b][k] != base["recordings"][b][k]:
                        ok = False
                        print("IDENTITY MISMATCH", b, k, results["none"]["recordings"][b][k], base["recordings"][b][k])
            for k in ("inside_stop_frames", "outside_false_stop_frames"):
                if results["none"]["set_O"][k] != base["set_O"][k]:
                    ok = False
                    print("IDENTITY MISMATCH set_O", k)
            for lab, o in base["set_O"]["objects"].items():
                n = results["none"]["set_O"]["objects"][lab]
                for k in ("stop_frames", "first_stop_m", "held_from_m", "false_stop_frames"):
                    if o.get(k) != n.get(k):
                        ok = False
                        print("IDENTITY MISMATCH object", lab, k, n.get(k), o.get(k))
            if results["none"]["recordings"]["doubleT_obstacle"]["labelled"] != base["recordings"]["doubleT_obstacle"]["labelled"]:
                ok = False
                print("IDENTITY MISMATCH doubleT_obstacle labelled")
            print("IDENTITY (no rule == baseline gate):", "OK" if ok else "FAILED")
            if not ok:
                sys.exit(2)
    summ = {n: summarise(r) for n, r in results.items()}
    json.dump({"summary": summ, "vetoed": {n: r["vetoed"] for n, r in results.items()}},
              open(os.path.join(a.out, "screen.json"), "w"), indent=1)
    b = summ["none"]
    print(f"{'rule':20}{'emptySTOPfr':>12}{'emptyEp':>8}{'dT hits':>9}{'dT fp':>6}{'setO in':>9}{'O out':>6}{'bg':>4}  vetoed STOP rows per recording")
    for n, s in summ.items():
        print(f"{n:20}{s['empty_STOP_frames']:>12}{s['empty_STOP_episodes']:>8}{s['dT_obst_hits']:>9}{s['dT_obst_fp_events']:>6}"
              f"{s['setO_inside_stop_frames']:>9}{s['setO_outside_false']:>6}{s['setO_bg_frames']:>4}  {s['vetoed_rows']}")
    for n, s in summ.items():
        if n == "none":
            continue
        diffs = {k: (b["objects"][k], v) for k, v in s["objects"].items() if v != b["objects"][k]}
        if diffs or s["dT_obst_per_label"] != b["dT_obst_per_label"]:
            print(f"-- {n}: set O objects changed (stop_frames, first_stop_m, held_from_m) base -> rule:")
            for k, (x, y) in diffs.items():
                print(f"   {k:20} {x} -> {y}")
            if s["dT_obst_per_label"] != b["dT_obst_per_label"]:
                print("   doubleT_obstacle per label:", b["dT_obst_per_label"], "->", s["dT_obst_per_label"])


if __name__ == "__main__":
    main()
