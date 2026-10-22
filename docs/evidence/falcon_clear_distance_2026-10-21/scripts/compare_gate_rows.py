#!/usr/bin/env python3
"""Paired per-row comparison of two regression_gate work directories (control = unmodified v1.2.0, candidate) and the rule
trace of run_cache_trace.py. Every row of every piece: all fields except timings and the clear distance (top level and
health) must be identical; every changed clear must be lower and carry a rule; the trace's clear must equal the gate row's.

    compare_gate_rows.py CTL_WORK CAND_WORK TRACE_DIR --out DIR [--ctl-trace-dir DIR]
"""
import argparse, glob, json, os, random, sys
ap = argparse.ArgumentParser()
ap.add_argument("ctl"); ap.add_argument("cand"); ap.add_argument("trace")
ap.add_argument("--out", required=True)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)


def strip(d):
    d = json.loads(json.dumps(d))
    d.pop("timing_ms", None)
    for k in ("clear_distance",):
        d.pop(k, None)
    h = d.get("health")
    if isinstance(h, dict):
        h.pop("clear_distance", None)
        h.pop("latency_p95_ms", None)
    d.pop("latency_ms", None)
    if isinstance(h, dict):
        # the latency warning is the machine's speed (health.latency_budget_ms on a shared runner), not the scene: it
        # sets `level` and a message but, with health.latency_affects_decision false, never `decision_level`
        h["messages"] = [m for m in h.get("messages", []) if not m.startswith("latency p95")]
        h.pop("level", None)
    return d


def latency_only_level(c, k):
    """rows whose `level` differs must differ in the latency message too (and decision_level must be equal)"""
    hc, hk = c.get("health") or {}, k.get("health") or {}
    if hc.get("level") == hk.get("level"):
        return True
    lat = lambda h: any(m.startswith("latency p95") for m in h.get("messages", []))  # noqa: E731
    return lat(hc) != lat(hk) and hc.get("decision_level") == hk.get("decision_level")


res = {"pieces": {}, "total_rows": 0, "other_field_diff_rows": 0, "raised_rows": 0, "changed_rows": 0, "changed_without_rule": 0,
       "rule_without_change": 0, "trace_vs_gate_clear_differ": 0, "by_rule": {}}
changes = []
for p in sorted(glob.glob(os.path.join(a.ctl, "*.jsonl"))):
    base = os.path.basename(p)
    q, t = os.path.join(a.cand, base), os.path.join(a.trace, base)
    rc = [json.loads(l) for l in open(p)]
    rk = [json.loads(l) for l in open(q)]
    tr = [json.loads(l) for l in open(t)]
    assert len(rc) == len(rk) == len(tr), (base, len(rc), len(rk), len(tr))
    n_ch = 0
    for i, (c, k, x) in enumerate(zip(rc, rk, tr)):
        res["total_rows"] += 1
        if strip(c) != strip(k):
            res["other_field_diff_rows"] += 1
        if not latency_only_level(c, k):
            res["level_differs_without_latency_message"] = res.get("level_differs_without_latency_message", 0) + 1
        if (c.get("health") or {}).get("level") != (k.get("health") or {}).get("level"):
            res["rows_level_differs_latency_only"] = res.get("rows_level_differs_latency_only", 0) + 1
        if abs(float(k["clear_distance"]) - x["clear"]) > 1e-9 and round(x["clear"], 1) != k["clear_distance"]:
            res["trace_vs_gate_clear_differ"] += 1
        if c["clear_distance"] != k["clear_distance"]:
            n_ch += 1
            res["changed_rows"] += 1
            res["raised_rows"] += k["clear_distance"] > c["clear_distance"]
            res["changed_without_rule"] += not x["rule"]
            res["by_rule"][x["rule"]] = res["by_rule"].get(x["rule"], 0) + 1
            changes.append((base[:-6], c["frame"], c["clear_distance"], k["clear_distance"], x["rule"], x["obstacle"], x["lost_msg"]))
        elif x["rule"]:
            res["rule_without_change"] += 1
    res["pieces"][base[:-6]] = {"rows": len(rc), "changed": n_ch}
with open(os.path.join(a.out, "clear_changes_pandar.tsv"), "w") as f:
    f.write("piece\tframe\told\tnew\trule\tstop\tlock_lost_message\n")
    for r in changes:
        f.write("\t".join(str(v) for v in r) + "\n")
json.dump(res, open(os.path.join(a.out, "compare_gate_rows.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
