#!/usr/bin/env python3
"""Reviewer script: for the 4 flips kept only because their surface has a single supporting return, would a bar of 1
return (instead of 2) have rejected them?  (Sensitivity of the 'count 2' constant on the same 98 snapshots.)"""
import json
from pathlib import Path

D = Path(__file__).resolve().parent / "out"
est = {(r["stem"], r["k"]): r for r in json.load(open(D / "noise_est.json"))}
cand = {(r["stem"], r["k"]): r for r in json.load(open(D / "snap_pad_wt_cand.json"))["rows"]}
n = 0
for key in [("new_data_52_0019", 5), ("new_data_81_0027", 10), ("new_data_112_0000", 7), ("new_data_115_0035", 1)]:
    e, c = est[key], cand[key]
    hide = c["top_new"] <= e["S"] + 0.05
    n += hide
    print(key, "top", c["top_new"], "S", round(e["S"], 3), "n_near", e["n_near"], "would be rejected with a bar of 1:", hide)
print("rejected with a bar of 1:", n, "of 4 (total would be", 85 + n, "of 98)")
