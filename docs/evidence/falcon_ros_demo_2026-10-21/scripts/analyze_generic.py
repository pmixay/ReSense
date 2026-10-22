#!/usr/bin/env python3
"""Summary of a trial on a bag without an offline reference: analyze_generic.py TRIALDIR EXPECTED_FRAMES"""
import json, re, statistics, sys, collections
d = sys.argv[1]; expected = int(sys.argv[2])
ev = [json.loads(l) for l in open(f"{d}/events.jsonl")]
times = dict(l.split()[:2] for l in open(f"{d}/times.txt")); t_cmd = float(times["player_cmd_start"])
ins = {}
for e in ev:
    if e["topic"] == "in": ins.setdefault(round(e["stamp"], 6), e["t"])
fr = {}
for e in ev:
    if e["topic"] == "status" and e.get("node") and e.get("stamp"):
        fr.setdefault(round(e["stamp"], 6), e)
def stats(a):
    if not a: return None
    a = sorted(a); return {"n": len(a), "median_s": round(statistics.median(a), 4), "p95_s": round(a[min(len(a)-1, int(.95*len(a)))], 4), "max_s": round(a[-1], 4)}
ages = [e["t"] - ins[s] for s, e in fr.items() if s in ins]
last = fr[max(fr)]["node"] if fr else {}
order = sorted(fr)
dec = collections.Counter(fr[s]["decision"] for s in order)
chg = []; prev = None
for s in order:
    if fr[s]["decision"] != prev: chg.append([order.index(s), fr[s]["decision"], fr[s].get("nearest_distance"), round(fr[s]["t"] - t_cmd, 2)]); prev = fr[s]["decision"]
mem = [float(m.group(1)) * (1024 if m.group(2) == "GiB" else 1) for l in open(f"{d}/docker_stats.txt") for m in [re.search(r"([\d.]+)(MiB|GiB)\s*/", l)] if m]
res = {"trial": d.rstrip("/").split("/")[-1], "expected_frames": expected, "frames_with_status": len(fr), "inputs_seen_by_recorder": len(ins),
       "decisions": dict(dec), "freshness_valid": sum(1 for e in fr.values() if e["freshness"].get("valid")),
       "freshness_reasons": dict(collections.Counter(e["freshness"].get("reason") for e in fr.values())),
       "result_age_status_minus_input_arrival": stats(ages),
       "node_source_age_s": stats([e["freshness"]["source_age_s"] for e in fr.values() if e["freshness"].get("source_age_s") is not None]),
       "node_last_frame_stats": {k: last.get(k) for k in ("frames", "dropped_frames", "catchup_skipped", "rss_peak_mb", "fps", "cpu_cores")},
       "container_mem_MiB_max": max(mem) if mem else None, "first_status_since_player_cmd_s": round(fr[order[0]]["t"] - t_cmd, 2) if order else None,
       "last_status_since_player_cmd_s": round(fr[order[-1]]["t"] - t_cmd, 2) if order else None,
       "decision_changes_[index_in_processed,decision,nearest_m,since_player_cmd_s]": chg}
print(json.dumps(res, indent=1))
