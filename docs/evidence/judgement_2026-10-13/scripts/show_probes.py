import glob
import json
import os
import subprocess
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from summarize_empty import summarize
for f in sorted(glob.glob("out/probe/*.jsonl")):
    name = os.path.basename(f)[:-6]
    R = [json.loads(line) for line in open(f)]
    if not R:
        continue
    dec = [r["decision"] for r in R]
    cnt = {k: dec.count(k) for k in ("GO", "CAUTION", "STOP", "FAULT")}
    if name.startswith("doubleT_obstacle"):
        first = next((r["i"] for r in R if r["decision"] == "STOP"), None)
        after = [r for r in R if r["i"] >= 8]
        s_after = sum(r["decision"] == "STOP" for r in after)
        pers = [r for r in R if 8 <= r["i"] <= 68]
        print(f"{name:42s} n={len(R)} {cnt} firstSTOP frame {first}; STOP after fr8 {s_after}/{len(after)}; person fr8-68 {sum(r['decision']=='STOP' for r in pers)}/{len(pers)}")
    elif name.startswith("cloud_with_fake_obj"):
        out = subprocess.run([sys.executable, "scripts/score_objects.py", f, "/home/user/ReSense/labels/cloud_with_fake_obj.json",
                              f.replace(".jsonl", ".score.json")], capture_output=True, text=True).stdout
        S = json.load(open(f.replace(".jsonl", ".score.json")))["objects"]
        row = " ".join(f"{k[:9]}:{v['first_stop_d']}" for k, v in S.items())
        print(f"{name:42s} n={len(R)} {cnt} firstSTOP(m) {row}")
    else:
        s = summarize(f)
        print(f"{name:42s} n={len(R)} {cnt} STOP ep {s['stop_episodes']} frames {s['counts']['STOP']} CAUTION {s['frac']['CAUTION']:.2f}")
