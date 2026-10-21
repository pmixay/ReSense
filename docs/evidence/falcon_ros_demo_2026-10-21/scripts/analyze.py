#!/usr/bin/env python3
"""Summarise one trial (events.jsonl from recorder.py) and compare with the offline cold-start replay.
analyze.py TRIALDIR COLDSTART.jsonl.xz [--first-frame 2719] > summary.json"""
import json, lzma, re, statistics, sys, collections

d = sys.argv[1]; cold_path = sys.argv[2]
ev = [json.loads(l) for l in open(f"{d}/events.jsonl")]
cold = [json.loads(l) for l in lzma.open(cold_path, "rt")]
times = dict(l.split()[:2] for l in open(f"{d}/times.txt"))
t_cmd = float(times["player_cmd_start"])
stamps = [c["stamp"] for c in cold]

def idx(stamp):
    j = min(range(len(stamps)), key=lambda k: abs(stamps[k] - stamp))
    return j if abs(stamps[j] - stamp) < 2e-3 else None

ins = {}
for e in ev:
    if e["topic"] == "in":
        j = idx(e["stamp"]);
        if j is not None and j not in ins: ins[j] = e["t"]
frames = {}          # bag index -> first frame-kind status
extra_frame_status = 0
for e in ev:
    if e["topic"] == "status" and (e.get("node") or {}) and e.get("stamp"):
        j = idx(e["stamp"])
        if j is None: continue
        if j in frames: extra_frame_status += 1; continue
        frames[j] = e
first_in = min(ins.values()) if ins else None
n = len(cold)
res = {"trial": d.rstrip("/").split("/")[-1], "bag_frames": n, "frames_with_status": len(frames),
       "frames_seen_by_recorder_input_sub": len(ins), "duplicate_frame_status": extra_frame_status}
res["missing_frames"] = [cold[j]["frame"] for j in range(n) if j not in frames]
dec = collections.Counter(frames[j]["decision"] for j in frames)
res["decisions_live"] = dict(dec)
res["decisions_offline_replay"] = dict(collections.Counter(c["decision"] for c in cold))
diff = [cold[j]["frame"] for j in range(n) if j in frames and frames[j]["decision"] != cold[j]["decision"]]
res["frames_with_different_decision_than_offline_cold_replay"] = len(diff)
res["frames_not_processed"] = len(res["missing_frames"])
res["different_decision_frames"] = diff
# first STOP
def first_stop(src):
    for j in range(n):
        if src(j) == "STOP": return j
fs_live = first_stop(lambda j: frames[j]["decision"] if j in frames else None)
fs_off = first_stop(lambda j: cold[j]["decision"])
def at(j):
    if j is None: return None
    e = frames[j]; return {"frame": cold[j]["frame"], "bag_s": round(j * 0.1, 1) if False else round(cold[j]["bag_t"] - cold[0]["bag_t"], 2),
        "nearest_m": e.get("nearest_distance"), "since_player_cmd_s": round(e["t"] - t_cmd, 2),
        "since_first_input_s": None if first_in is None else round(e["t"] - first_in, 2)}
res["first_stop_live"] = at(fs_live)
res["first_stop_offline"] = {"frame": cold[fs_off]["frame"], "nearest_m": cold[fs_off]["nearest"],
                             "bag_s": round(cold[fs_off]["bag_t"] - cold[0]["bag_t"], 2)}
# result age: status arrival minus input arrival of the same frame
ages = [frames[j]["t"] - ins[j] for j in frames if j in ins]
def stats(a):
    if not a: return None
    a = sorted(a); p = lambda q: a[min(len(a) - 1, int(q * len(a)))]
    return {"n": len(a), "median_s": round(statistics.median(a), 4), "p95_s": round(p(0.95), 4), "max_s": round(a[-1], 4), "min_s": round(a[0], 4)}
res["result_age_status_arrival_minus_input_arrival"] = stats(ages)
res["node_source_age_s_publication"] = stats([frames[j]["freshness"].get("source_age_s") for j in frames if frames[j]["freshness"].get("source_age_s") is not None])
res["node_residence_age_s"] = stats([frames[j]["freshness"].get("residence_age_s") for j in frames if frames[j]["freshness"].get("residence_age_s") is not None])
res["freshness_valid_reasons"] = dict(collections.Counter(frames[j]["freshness"].get("reason") for j in frames))
res["freshness_valid_count"] = sum(1 for j in frames if frames[j]["freshness"].get("valid"))
last = frames[max(frames)]["node"] if frames else {}
res["node_last_frame_stats"] = {k: last.get(k) for k in ("frames", "dropped_frames", "catchup_skipped", "rss_peak_mb", "fps", "cpu_cores", "input_period_ms")}
res["node_latency_ms_max"] = max((frames[j]["node"].get("latency_ms") or 0) for j in frames) if frames else None
# decision stream consistency: /resense/decision String vs status
ds = [e["v"] for e in ev if e["topic"] == "decision"]
ss = [e["decision"] for e in ev if e["topic"] == "status"]
res["decision_topic_equals_status_sequence"] = ds == ss
res["decision_topic_messages"] = len(ds)
# docker stats RSS
mem = []
for l in open(f"{d}/docker_stats.txt"):
    m = re.search(r"([\d.]+)(MiB|GiB)\s*/", l)
    if m: mem.append(float(m.group(1)) * (1024 if m.group(2) == "GiB" else 1))
res["container_mem_MiB"] = {"max": max(mem), "median": statistics.median(mem), "samples": len(mem)} if mem else None
# changes of decision over time (live)
chg = []; prev = None
for j in sorted(frames):
    if frames[j]["decision"] != prev:
        chg.append([cold[j]["frame"], frames[j]["decision"], frames[j].get("nearest_distance")]); prev = frames[j]["decision"]
res["decision_changes_live_[frame,decision,nearest_m]"] = chg
# STOP runs
def runs(seq):
    out = []; s = None
    for j in range(n):
        v = seq(j) == "STOP"
        if v and s is None: s = j
        if not v and s is not None: out.append([cold[s]["frame"], cold[j - 1]["frame"]]); s = None
    if s is not None: out.append([cold[s]["frame"], cold[n - 1]["frame"]])
    return out
res["stop_runs_live"] = runs(lambda j: frames[j]["decision"] if j in frames else None)
res["stop_runs_offline"] = runs(lambda j: cold[j]["decision"])
res["non_stop_frames_after_frame_3060_live"] = [cold[j]["frame"] for j in range(n) if cold[j]["frame"] >= 3060 and (j not in frames or frames[j]["decision"] != "STOP")]
print(json.dumps(res, indent=1))
