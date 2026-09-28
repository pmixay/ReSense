"""One jury-chain capture (listener.py output) -> per-run summary: frames with a result, decisions
per bag frame, first STOP, STOP distances, non-STOP frames after the first STOP, end-to-end latency
(cloud arrival at the listener -> status with the same stamp), the node's own latency, CPU and RSS.

    python analyze.py <run dir> <bag> [bag_stamps.json]
"""
import json
import sys

import numpy as np


def analyze(run_dir: str, bag: str, stamps_path: str = "bag_stamps.json") -> dict:
    hs = [h for _, h in json.load(open(stamps_path))[bag]]
    idx = {round(h, 4): i for i, h in enumerate(hs)}
    rows = [json.loads(line) for line in open(f"{run_dir}/listen.jsonl")]
    cloud_t = {}
    for x in rows:
        if x["k"] == "cloud":
            cloud_t.setdefault(round(x["stamp"], 4), x["t"])
    frames = []
    for x in rows:
        if x["k"] != "status":
            continue
        s = json.loads(x["v"])
        key = round(s["stamp"], 4) if s.get("stamp") else None
        if idx.get(key) is None:
            continue
        frames.append(dict(i=idx[key], t=x["t"], dec=s.get("decision"), d=s.get("nearest_distance"),
                           fresh=(s.get("freshness") or {}).get("reason"),
                           e2e=(x["t"] - cloud_t[key]) * 1e3 if key in cloud_t else None,
                           node=s.get("node") or {}))
    seen = sorted({r["i"] for r in frames})
    first_cloud = min(cloud_t.values()) if cloud_t else None
    dec = {}
    for r in frames:
        dec.setdefault(r["i"], r["dec"])
    seq = [dec[i] for i in seen]
    stops = [r for r in frames if r["dec"] == "STOP"]
    first = stops[0] if stops else None
    e2e = np.array([r["e2e"] for r in frames if r["e2e"] is not None])
    e2e_cur = np.array([r["e2e"] for r in frames if r["e2e"] is not None and r["fresh"] == "current"])
    lat = np.array([r["node"].get("latency_ms", np.nan) for r in frames], float)
    runs = []
    for i in seen:
        if runs and runs[-1][0] == dec[i]:
            runs[-1][2] = i
            runs[-1][3] += 1
        else:
            runs.append([dec[i], i, i, 1])
    dist = [r["d"] for r in stops if r["d"] is not None]

    def pct(a, q):
        return round(float(np.percentile(a, q)), 1) if len(a) else None

    return dict(
        bag=bag, run=run_dir.rstrip("/").split("/")[-1], frames_in_bag=len(hs), frames_with_result=len(seen),
        clouds_seen_by_listener=len(cloud_t), counts={d: seq.count(d) for d in set(seq)},
        first_stop_frame=first["i"] if first else None,
        first_stop_after_first_cloud_s=round(first["t"] - first_cloud, 2) if first and first_cloud else None,
        first_stop_fresh=first["fresh"] if first else None,
        stop_dist=[round(min(dist), 1), round(max(dist), 1)] if dist else None,
        e2e_p50=pct(e2e, 50), e2e_p95=pct(e2e, 95), e2e_cur_p95=pct(e2e_cur, 95),
        e2e_max=round(float(e2e.max()), 1) if len(e2e) else None,
        node_lat_p95=round(float(np.nanpercentile(lat, 95)), 1),
        cpu_cores=frames[-1]["node"].get("cpu_cores"), rss_mb=frames[-1]["node"].get("rss_peak_mb"),
        dropped=frames[-1]["node"].get("dropped_frames"), catchup_skipped=frames[-1]["node"].get("catchup_skipped"),
        non_stop_runs_after_first_stop=[r for r in runs if first and r[1] > first["i"] and r[0] != "STOP"])


if __name__ == "__main__":
    print(json.dumps(analyze(*sys.argv[1:]), indent=1))
