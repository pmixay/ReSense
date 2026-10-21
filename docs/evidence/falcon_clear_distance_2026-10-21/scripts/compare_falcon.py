#!/usr/bin/env python3
"""Paired per-row comparison of two run_falcon.py outputs (control = unmodified v1.2.0, candidate = switches on).
Checks F1-F5 of PROTOCOL.md and writes every changed row.

    compare_falcon.py CONTROL_PREFIX CAND_PREFIX --out OUTDIR
"""
import argparse, json, os, sys

ap = argparse.ArgumentParser()
ap.add_argument("ctl")
ap.add_argument("cand")
ap.add_argument("--out", required=True)
a = ap.parse_args()
T = {"decode_ms", "detect_ms", "total_ms"}


def load(p):
    return [json.loads(l) for l in open(p)]


rc, rk = load(a.ctl + ".jsonl"), load(a.cand + ".jsonl")
xc, xk = load(a.ctl + ".x.jsonl"), load(a.cand + ".x.jsonl")
cc, ck = load(a.ctl + ".c.jsonl"), load(a.cand + ".c.jsonl")
n = len(rc)
assert len(rk) == len(xk) == len(ck) == len(cc) == len(xc) == n, "row counts differ"
os.makedirs(a.out, exist_ok=True)
res = {"rows": n}

# F1: every field but clear and timings
bad = [i for i in range(n) if {k: v for k, v in rc[i].items() if k not in T | {"clear"}} !=
       {k: v for k, v in rk[i].items() if k not in T | {"clear"}}]
res["F1_record_other_fields_differ_rows"] = len(bad)
res["F1_node_decision_differ_rows"] = sum(cc[i]["decision"] != ck[i]["decision"] or
                                          cc[i]["conservative"]["decision"] != ck[i]["conservative"]["decision"] or
                                          cc[i]["small_candidate"]["decision"] != ck[i]["small_candidate"]["decision"]
                                          for i in range(n))
# other terms of the health the record does not carry
res["F1_x_terms_differ_rows"] = sum({k: v for k, v in xc[i].items() if k not in ("clear_raw", "rule", "bed_excess")} !=
                                    {k: v for k, v in xk[i].items() if k not in ("clear_raw", "rule", "bed_excess")} for i in range(n))

# F2 / F5
changed = [i for i in range(n) if rc[i]["clear"] != rk[i]["clear"]]
res["changed_rows"] = len(changed)
res["F2_raised_rows"] = sum(rk[i]["clear"] > rc[i]["clear"] for i in changed)
by_rule = {}
for i in changed:
    by_rule.setdefault(xk[i]["rule"], []).append(i)
res["changed_by_rule"] = {k: len(v) for k, v in by_rule.items()}
for r in ("lost_model", "lost_bed"):
    res[f"F2_{r}_not_zero"] = sum(rk[i]["clear"] != 0.0 for i in by_rule.get(r, []))
res["F2_lost_bed_rows_without_bed_excess_gt_0"] = sum(not ((xk[i].get("bed_excess") or -1) > 0) for i in by_rule.get("lost_bed", []))
res["F2_round_down_delta_not_0.1"] = sum(abs(round(rc[i]["clear"] - rk[i]["clear"], 1) - 0.1) > 1e-9
                                         for r in ("round_down_obstacle", "round_down_candidate") for i in by_rule.get(r, []))
res["F5_changed_without_rule"] = sum(not xk[i]["rule"] for i in changed)
res["F5_rule_without_change"] = sum(bool(xk[i]["rule"]) and rc[i]["clear"] == rk[i]["clear"] for i in range(n))
res["control_has_rule_key"] = any(x.get("rule") for x in xc)
with open(os.path.join(a.out, "clear_changes_falcon.tsv"), "w") as f:
    f.write("frame\tdecision\told\tnew\trule\tmin_det_d\tlock\n")
    for i in changed:
        d = min((x["d"] for x in rc[i]["dets"]), default="")
        f.write(f"{i}\t{rc[i]['decision']}\t{rc[i]['clear']}\t{rk[i]['clear']}\t{xk[i]['rule']}\t{d}\t{rc[i]['rail_lock']}\n")

# F3: the 39 rows
person = [i for i in range(4373, 4415) if rc[i]["decision"] != "STOP" and rc[i]["clear"] > 0]
res["F3_person_rows"] = len(person)
res["F3_person_rows_clear_not_zero"] = [i for i in person if rk[i]["clear"] != 0.0]
res["F3_node_not_zero"] = [i for i in person if ck[i]["conservative"]["clear"] != 0.0 or ck[i]["small_candidate"]["clear"] != 0.0]

# F3b (amendment 1): the person rows in which the bed is lost by the rule (trace bed_excess > 0) are 0; the rest is the residual
lostbed = [i for i in person if (xk[i].get("bed_excess") or -1) > 0]
resid = [i for i in person if i not in lostbed]
res["F3b_rows_bed_lost"] = len(lostbed)
res["F3b_bed_lost_rows_clear_not_zero"] = [i for i in lostbed if rk[i]["clear"] != 0.0 or ck[i]["conservative"]["clear"] != 0.0 or ck[i]["small_candidate"]["clear"] != 0.0]
res["F3b_residual_rows_bed_ok"] = resid
res["F3b_residual_control_clear"] = {i: rc[i]["clear"] for i in resid}
res["F3b_residual_candidate_clear"] = {i: rk[i]["clear"] for i in resid}

# F4: clear <= STOP distance
def viol(rows, key):
    out = []
    for i, r in enumerate(rows):
        if r["decision"] == "STOP" and r["dets"]:
            if key(i) > min(d["d"] for d in r["dets"]) + 1e-9:
                out.append(i)
    return out

res["F4_detector_violations_control"] = len(viol(rc, lambda i: rc[i]["clear"]))
res["F4_detector_violations_candidate"] = len(viol(rk, lambda i: rk[i]["clear"]))
res["F4_node_conservative_violations_control"] = len(viol(rc, lambda i: cc[i]["conservative"]["clear"]))
res["F4_node_conservative_violations_candidate"] = len(viol(rk, lambda i: ck[i]["conservative"]["clear"]))
res["F4_node_small_candidate_violations_control"] = len(viol(rc, lambda i: cc[i]["small_candidate"]["clear"]))
res["F4_node_small_candidate_violations_candidate"] = len(viol(rk, lambda i: ck[i]["small_candidate"]["clear"]))
# node path: only lowered
for pol in ("conservative", "small_candidate"):
    res[f"node_{pol}_raised_rows"] = sum(ck[i][pol]["clear"] > cc[i][pol]["clear"] for i in range(n))
    res[f"node_{pol}_changed_rows"] = sum(ck[i][pol]["clear"] != cc[i][pol]["clear"] for i in range(n))
with open(os.path.join(a.out, "clear_changes_falcon_node.tsv"), "w") as f:
    f.write("frame\tdecision\tpolicy\told\tnew\n")
    for i in range(n):
        for pol in ("conservative", "small_candidate"):
            if ck[i][pol]["clear"] != cc[i][pol]["clear"]:
                f.write(f"{i}\t{rc[i]['decision']}\t{pol}\t{cc[i][pol]['clear']}\t{ck[i][pol]['clear']}\n")
json.dump(res, open(os.path.join(a.out, "compare_falcon.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
