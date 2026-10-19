#!/usr/bin/env python3
"""Attribution of the v5 gate failures by single-recording runs with the gate's own harness (eval_real.run_piece,
devrun.py), and the harness controls. Prints STOP frames / episodes / set O scores per configuration."""
import json, os, sys
os.chdir("/data/work_k2/trees/v5"); sys.path[:0] = [os.getcwd(), os.getcwd() + "/scripts"]
from score_fake_objects import score
from resense.metrics import load_gt
D, G = "/data/work_k2/dev", "/data/work_k2/gates"
def rows(p): return [json.loads(l) for l in open(p)]
def norm(r):
    r = dict(r); r.pop("timing_ms", None); h = dict(r.get("health") or {}); h.pop("latency_p95_ms", None)
    h["messages"] = [m for m in h.get("messages", []) if "latency" not in m]; h.pop("level", None); h.pop("decision_level", None); r["health"] = h
    return r
def stops(R):
    s = [i for i, r in enumerate(R) if r["obstacle"]]
    return s, sum(1 for i in s if i - 1 not in s)
print("controls: the dev harness reproduces the gate rows (frames differing, timing/latency-level excluded)")
for a, b in ((f"{G}/v5a/work/doubleT_platform.jsonl", f"{D}/dp/v5a.jsonl"), (f"{G}/base/work/doubleT_platform.jsonl", f"{D}/dp/base_off.jsonl"),
             (f"{G}/v5b/work/roundT_doubleT.jsonl", f"{D}/yamlchk/yaml.jsonl"), (f"{G}/base/work/roundT_squareT_pressureGate_squareT.jsonl", f"{D}/sq/off.jsonl")):
    A, B = rows(a), rows(b)
    print(" ", os.path.relpath(b, D), "vs gate", os.path.relpath(a, G), ":", sum(norm(x) != norm(y) for x, y in zip(A, B)), "of", len(A))
print("doubleT_platform (gate: base 1 episode, v5a / v5b 2)")
for tag in ("base_off", "k1", "v5a", "v5a_noK1", "v5b_noK1"):
    s, e = stops(rows(f"{D}/dp/{tag}.jsonl")); print(f"  {tag:9s} STOP frames {s} episodes {e}")
print("roundT_doubleT (gate: base 0, v5a 1 episode frames 96-99, v5b 0)")
for tag in ("k1", "v5a_noK1"):
    R = rows(f"{D}/rd/{tag}.jsonl"); s, e = stops(R)
    print(f"  {tag:9s} STOP frames {s} episodes {e} joint_used at them {[R[i]['track'].get('joint_used') for i in s]}")
print("set O (gate: base small_center 32 / 55.8 m, bg 0; v5a 30 / 52.5, bg 5; v5b 30 / 52.5, bg 0)")
gt = load_gt("labels/cloud_with_fake_obj.json")
for tag in ("k1", "v5a_noK1", "v5b_noK1"):
    objs, bg = score(rows(f"{D}/so/{tag}.jsonl"), gt)
    sc = objs["small_center"]
    print(f"  {tag:9s} small_center STOP {sc['alarm_frames']} first {sc['first_alarm_m']} m | background {bg['background_alarm_frames']} frames {bg['background_alarm_ids']} ids")
print("configs: k1 = walls_smoothing_distance 1.5 only; v5a_noK1 / v5b_noK1 = the variant with walls_smoothing_distance 0")
