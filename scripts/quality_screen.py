#!/usr/bin/env python3
"""One command for a detector candidate: the regression gate, the monitoring diagnostics and the
processing-history stress, summarised against the four open quality problems (27.09).

    python scripts/quality_screen.py --name base                       # the checkout as it is
    python scripts/quality_screen.py --name c1 --set gauge.axis_union=1 [--set ...] [--config FILE]
    python scripts/quality_screen.py --name c1 --quick                 # six recordings + set O only

It runs, from the checkout it lives in, on the caches of ``--cache``:

1. ``scripts/regression_gate.py`` against ``--baseline`` (every gated metric identical or better;
   the per-frame outputs go to ``<work>/<name>/gate``);
2. ``scripts/quality_acceptance.py`` against the reference outputs ``--reference``: the GO
   diagnostic overclaims on set O (an object with points in the rail-referenced envelope nearer
   than ``clear_distance`` while the decision is GO) and the monitoring cost (newly uncertain
   frames, median ``clear_distance`` retention) on the five empty recordings and the ride;
3. ``scripts/history_stress.py``: false STOPs of obstacle-free recordings under the three captured
   node histories and seeded dropped-frame / catch-up / offset / dither histories.

``summary.json`` holds the four headline problems: (1) the edge objects of set O (#4 and #6:
first STOP distance, STOP frames), (2) the ride's false alarm events and STOP episodes, (3) the GO
overclaims, (4) the history-dependent false STOPs; plus the gate verdict. A machine-wide lock
(``<work>/.cpu.lock``) serialises the heavy runs of parallel sessions on one machine.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASELINE = os.path.join(ROOT, "docs", "evidence", "results", "regression_baseline_2026-09-26_ride_p3d.json")
EDGE = ("small_edge_inside", "big_edge_inside")


def _run(cmd, log):
    t0 = time.time()
    with open(log, "w", encoding="utf-8") as fh:
        r = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return r.returncode, round(time.time() - t0, 1)


def summarize(work: str, gate_rc: int, quick: bool) -> dict:
    gate = json.load(open(os.path.join(work, "gate.json"), encoding="utf-8"))
    so = gate.get("set_O") or {}
    objs = so.get("objects") or {}
    edge = {k: {f: objs.get(k, {}).get(f) for f in ("stop_frames", "first_stop_m", "held_from_m",
                                                     "advisory_frames", "visible_frames")} for k in EDGE}
    inside = {k: {f: o.get(f) for f in ("stop_frames", "first_stop_m", "held_from_m")}
              for k, o in objs.items() if o.get("in_gauge")}
    outside = {k: o.get("false_stop_frames") for k, o in objs.items() if o.get("in_gauge") is False}
    ride = gate.get("ride") or {}
    rec = gate.get("recordings") or {}
    lab = (rec.get("doubleT_obstacle") or {}).get("labelled") or {}
    out = {
        "gate": {"exit_code": gate_rc, "passed": gate_rc == 0},
        "p1_edge_objects": edge,
        "p2_ride": {k: ride.get(k) for k in ("alarm_events", "stop_episodes", "alarm_frames")} if not quick else None,
        "five_empty": gate.get("five_empty"),
        "set_O": {"inside_stop_frames": so.get("inside_stop_frames"),
                  "outside_false_stop_frames": so.get("outside_false_stop_frames"),
                  "background": so.get("background"), "inside": inside, "outside": outside},
        "doubleT_obstacle": {"first_alarm_frame": (rec.get("doubleT_obstacle") or {}).get("first_alarm_frame"),
                             "per_label": lab.get("per_label"), "fp_events": lab.get("fp_events")},
    }
    acc_path = os.path.join(work, "acceptance.json")
    if os.path.exists(acc_path):
        acc = json.load(open(acc_path, encoding="utf-8"))
        tot = acc["set_O_candidate"]["totals"]
        out["p3_overclaims"] = {"GO": tot["target_by_decision"].get("GO", 0), "target": tot["target"],
                                "by_decision": tot["target_by_decision"],
                                "monitoring_cost_passed": acc["monitoring_cost_passed"],
                                "monitoring_cost": {k: {"newly_uncertain_pp": round(v["newly_uncertain_percentage_points"], 3),
                                                        "clear_median_fraction": round(v["clear_median_fraction"], 4)}
                                                    for k, v in acc["monitoring_cost"].items()}}
    hist_path = os.path.join(work, "history.json")
    if os.path.exists(hist_path):
        out["p4_history"] = json.load(open(hist_path, encoding="utf-8"))["totals"]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--work", default="/data/work")
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--config", default=os.path.join(ROOT, "configs", "default.yaml"))
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--baseline", default=BASELINE)
    ap.add_argument("--reference", default="/data/work/base/gate", help="reference per-frame outputs (quality_acceptance)")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--quick", action="store_true", help="no ride: six recordings and set O (gate --allow ride/set F)")
    ap.add_argument("--no-history", action="store_true")
    ap.add_argument("--no-lock", action="store_true")
    a = ap.parse_args(argv)
    work = os.path.join(a.work, a.name)
    os.makedirs(work, exist_ok=True)
    sets = [x for s in a.set for x in ("--set", s)]
    lock = None
    if not a.no_lock:
        lock = open(os.path.join(a.work, ".cpu.lock"), "w")
        print(f"[{a.name}] waiting for the machine lock ...", flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        cache = a.cache
        allow = []
        if a.quick:
            # a cache view without the ride: the gate then skips the ride and set F
            cache = os.path.join(work, "cache_noride")
            os.makedirs(cache, exist_ok=True)
            for n in os.listdir(a.cache):
                if n != "new_data" and not os.path.exists(os.path.join(cache, n)):
                    os.symlink(os.path.join(a.cache, n), os.path.join(cache, n))
            allow = ["--allow", "ride.*", "--allow", "set_F_straight.*"]
        gate_cmd = [sys.executable, "scripts/regression_gate.py", "--cache", cache, "--config", a.config, *sets,
                    "--jobs", str(a.jobs), "--work", os.path.join(work, "gate"), "--out", os.path.join(work, "gate.json"),
                    "--baseline", a.baseline, *allow]
        print(f"[{a.name}] gate ...", flush=True)
        rc, s = _run(gate_cmd, os.path.join(work, "gate.log"))
        print(f"[{a.name}] gate exit {rc} ({s} s)", flush=True)
        if not a.quick and os.path.isdir(a.reference):
            rc2, s2 = _run([sys.executable, "scripts/quality_acceptance.py", "--reference", a.reference,
                            "--candidate", os.path.join(work, "gate"), "--out", os.path.join(work, "acceptance.json")],
                           os.path.join(work, "acceptance.log"))
            print(f"[{a.name}] acceptance exit {rc2} ({s2} s)", flush=True)
        if not a.no_history:
            rc3, s3 = _run([sys.executable, "scripts/history_stress.py", "--cache", a.cache, "--config", a.config, *sets,
                            "--jobs", str(a.jobs), "--out", os.path.join(work, "history.json")],
                           os.path.join(work, "history.log"))
            print(f"[{a.name}] history exit {rc3} ({s3} s)", flush=True)
    finally:
        if lock is not None:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()
    summary = summarize(work, rc, a.quick)
    summary["name"], summary["sets"], summary["config"] = a.name, a.set, a.config
    with open(os.path.join(work, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
