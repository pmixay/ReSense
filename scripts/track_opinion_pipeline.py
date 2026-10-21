#!/usr/bin/env python3
"""The track opinion (``tracking.doubt_model``) end to end, one command (21.10, card G2).

Collects every training / test row on the detector of this checkout with the opinion pinned off (as
``scripts/track_opinion.py collect`` always did), trains the model, the cross-fitting fold models and the
27.09 recipe for comparison, and writes the model, its report and the fold models:

    python scripts/track_opinion_pipeline.py --cache /data/cache --work /data/work/opinion \\
        [--falcon-rows <falcon_multi off_*.rows.npz> --falcon-records <ctl jsonl>] [--jobs 4] \\
        [--export resense/models/track_opinion_1.3.json]

Re-running it resumes (an existing collection is reused; ``--fresh`` collects again). Stages:

1. ``collect``: negatives (the ride in the gate's 8 pieces, the five obstacle-free recordings), labelled
   tests (set O, ``doubleT_obstacle``), synthetic positives ray-cast into ride frames (``POSITIVE_SETS``), the
   crossing-person test of the 27.09 recipe. Injection files follow a fixed rule (``files_by_rule``): never
   within 3 split files of a test file (set F straight, the far-target set of the protocol).
2. ``r0``: the 27.09 recipe (19 features, its positives) on this detector: the reproduction row.
3. ``model``: the candidate (``CANDIDATE``), trained on every training group; its threshold is chosen on
   held-out groups (``track_opinion.py train --pick``).
4. ``folds``: the candidate retrained without each fold (ride pieces 0-1, 2-3, 4-5, 6-7; the five recordings),
   for ``scripts/opinion_crossfit.py`` and the cross-fitted gain rows.

G3 (``docs/evidence/heldout_2026-10-15``) is never read.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TO = os.path.join(HERE, "track_opinion.py")
EMPTY = ("doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
         "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch")
SET_F_FILES = (46, 68, 98, 140, 168, 172)            # regression_gate.SET_F_STRAIGHT
FAR_TEST_FILES = (184, 198, 210, 7, 19, 154, 11, 158)  # PROTOCOL §3 H6 (rule applied 21.10)
OFF = ['--set', 'tracking.doubt_model=""']
R0_FEATURES = ("distance,abs_lateral,is_low,frac_low,hits,lat_std,lat_jump,cz_std,hmax_mean,hmin_mean,len_mean,"
               "width_mean,height_mean,gauge_frac,frac_demoted,frac_column,frac_beyond,dist_rough,hit_fraction")


def files_by_rule(moving: bool, stride: int, offset: int = 0):
    """Ride split files for injection: moving (``speed_tracks`` >= 5 m/s) or standing (< 0.3 m/s), at least 4
    files from every test file and with 140 frames after the start, every ``stride``-th from ``offset``."""
    intake = json.load(open(os.path.join(ROOT, "docs/extended_dataset_intake.json")))["files"]
    test = SET_F_FILES + FAR_TEST_FILES
    ok = [f["n"] for f in intake if f["n"] <= 217 and all(abs(f["n"] - t) >= 4 for t in test)
          and (((f.get("speed_tracks") or 0.0) >= 5.0) if moving else ((f.get("speed_tracks") or 0.0) < 0.3))]
    return ok[offset::stride]


def positive_sets():
    """(name, collect arguments) of the synthetic positive collections."""
    mv, mv2, st = files_by_rule(True, 6), files_by_rule(True, 6, 3), files_by_rule(False, 3)
    j = lambda v: ",".join(str(x) for x in v)  # noqa: E731
    kinds = "person,hivis,box0.3,box0.5,box1.0,trolley,cable,cable_low,lowbox,railobj,dog,plank"
    return [
        # the 27.09 recipe's positives: 8 kinds on moving files, 6 kinds with the train standing
        ("r0_moving", ["--inject", "person,box0.5,box1.0,trolley,cable,lowbox,railobj,dog", "--files", j(mv[:12]),
                       "--start", "200", "--seed", "1"]),
        ("r0_standing", ["--inject", "person,box0.5,box1.0,trolley,lowbox,dog", "--files", j(st[:7]),
                         "--start", "35:120", "--seed", "2"]),
        ("r0_crossing", ["--inject", "person", "--files", j(mv[:10]), "--start", "60:150", "--cross", "1.0",
                         "--seed", "3", "--piece-tag", "_cross"]),
        # 1.3: more kinds, far starts, moving and crossing objects, the standing train
        ("p13_far", ["--inject", kinds, "--files", j(mv2), "--start", "150:250", "--frames", "140", "--seed", "11",
                     "--piece-tag", "_far"]),
        ("p13_standing", ["--inject", kinds, "--files", j(st), "--start", "30:180", "--seed", "12",
                          "--piece-tag", "_st"]),
        ("p13_toward", ["--inject", "person,hivis,trolley,dog", "--files", j(mv), "--start", "120:240",
                        "--move=0.5:3.0", "--seed", "13", "--piece-tag", "_tw"]),
        ("p13_away", ["--inject", "person,trolley,box1.0", "--files", j(st), "--start", "35:120",
                      "--move=-2.0:-0.5", "--seed", "14", "--piece-tag", "_aw"]),
        # 21.10 amendment 1 (PROTOCOL): positives fixed after the synthetic-versus-real check
        ("p13j_moving", ["--inject", "person,hivis,trolley,dog,box1.0,box0.5", "--files", j(mv), "--start", "60:250",
                         "--frames", "140", "--size-jitter", "0.3", "--seed", "16", "--piece-tag", "_jm"]),
        ("p13j_standing", ["--inject", "person,hivis,trolley,dog,box1.0,box0.5", "--files", j(st), "--start", "30:180",
                           "--size-jitter", "0.3", "--seed", "17", "--piece-tag", "_js"]),
        ("p13_rail_moving", ["--inject", "railobj,lowbox", "--files", j(mv + mv2), "--start", "60:200",
                             "--on-rail", "--size-jitter", "0.3", "--seed", "18", "--piece-tag", "_rm"]),
        ("p13_rail_standing", ["--inject", "railobj,lowbox", "--files", j(st), "--start", "30:150",
                               "--on-rail", "--size-jitter", "0.3", "--seed", "19", "--piece-tag", "_rs"]),
        ("p13_cross", ["--inject", "person,hivis,dog", "--files", j(mv2), "--start", "40:160", "--cross", "1.2",
                       "--seed", "15", "--piece-tag", "_cx"]),
    ]


CANDIDATE = {
    # filled from the development step (PROTOCOL §2); the record of every tried variant is the report
    "features": R0_FEATURES,
    "pos": ["r0_moving", "r0_standing", "p13_far", "p13_standing", "p13_toward", "p13_away", "p13_cross"],
    "args": ["--sticky", "--near", "25", "--extra", "10", "--pick", "0.5", "--seq-weight"],
}
FOLDS = {"A": "new_data:0,new_data:1", "B": "new_data:2,new_data:3", "C": "new_data:4,new_data:5",
         "D": "new_data:6,new_data:7", "E": ",".join(EMPTY)}


def run(cmd, log):
    print("+", " ".join(cmd), flush=True)
    with open(log, "a") as fh:
        fh.write("+ " + " ".join(cmd) + "\n")
        fh.flush()
        r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise SystemExit(f"failed ({r.returncode}): {' '.join(cmd)}; see {log}")


def collect(a, name, args):
    out = os.path.join(a.work, f"{name}.npz")
    if os.path.exists(out) and not a.fresh:
        return out
    run([sys.executable, TO, "collect", "--cache", a.cache, "--jobs", str(a.jobs), "--out", out] + OFF + args,
        os.path.join(a.work, "collect.log"))
    return out


def train(a, name, features, pos, args, exclude="", export=""):
    rep = os.path.join(a.work, f"{name}_report.json")
    cmd = [sys.executable, TO, "train", "--neg", *a.neg, "--pos", *[a.data[p] for p in pos],
           "--test", *a.tests, "--features", features, "--report", rep,
           "--oof-out", os.path.join(a.work, f"{name}_oof.npz")] + args
    if exclude:
        cmd += ["--exclude", exclude]
    cmd += ["--export", export or os.path.join(a.work, f"{name}.json")]
    run(cmd, os.path.join(a.work, f"train_{name}.log"))
    return json.load(open(rep))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--work", required=True)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--stages", default="collect,r0,model,folds")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--falcon-rows", default="", help="Falcon rows in the collect layout (as negatives / test)")
    ap.add_argument("--export", default="")
    a = ap.parse_args(argv)
    os.makedirs(a.work, exist_ok=True)
    stages = a.stages.split(",")
    a.data = {}
    a.data["ride"] = collect(a, "neg_ride", ["--bag", "new_data", "--chunks", "8"])
    a.data["empty"] = collect(a, "neg_empty", ["--bag", ",".join(EMPTY)])
    a.data["setO"] = collect(a, "test_setO", ["--bag", "cloud_with_fake_obj"])
    a.data["dto"] = collect(a, "test_dto", ["--bag", "doubleT_obstacle"])
    for name, args in positive_sets():
        a.data[name] = collect(a, name, args)
    a.neg = [a.data["ride"], a.data["empty"]]
    a.tests = [a.data["setO"], a.data["dto"], a.data["r0_crossing"]]
    if a.falcon_rows:
        a.tests.append(a.falcon_rows)
    summary = {}
    if "r0" in stages:
        summary["r0"] = train(a, "r0", R0_FEATURES, ["r0_moving", "r0_standing"],
                              ["--sticky", "--near", "25", "--extra", "10", "--pick", "0.5"])
    if "model" in stages:
        summary["model"] = train(a, "model", CANDIDATE["features"], CANDIDATE["pos"], CANDIDATE["args"],
                                 export=a.export)
    if "folds" in stages:
        summary["folds"] = {k: train(a, f"fold{k}", CANDIDATE["features"], CANDIDATE["pos"], CANDIDATE["args"],
                                     exclude=v)["heldout"] for k, v in FOLDS.items()}
    json.dump({"candidate": CANDIDATE, "folds": FOLDS, "positive_sets": positive_sets(),
               "summary": {k: (v.get("heldout") if k != "folds" else v) for k, v in summary.items()}},
              open(os.path.join(a.work, "pipeline.json"), "w"), indent=1)
    print(json.dumps({k: (v.get("heldout") if k != "folds" else v) for k, v in summary.items()}, indent=1)[:4000])


if __name__ == "__main__":
    main()
