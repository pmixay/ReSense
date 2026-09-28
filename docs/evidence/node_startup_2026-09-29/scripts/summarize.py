"""A/B of the node's start-up through the jury chain: per run and per condition (image x bag x
cache / player), the latency of the first results and of all results, the first STOP and the
decisions, from the judge's listener captures (``../judgement_2026-09-28/scripts/listener.py``).

    python summarize.py <runs dir> <bag_stamps.json> > summary.json
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../judgement_2026-09-28/scripts"))
from analyze import analyze  # noqa: E402


def first_seconds(run_dir, bag, stamps_path, window=3.0):
    """e2e (listener: cloud arrival -> status with the same stamp) of the clouds of the first
    ``window`` s after the first cloud arrived."""
    rows = [json.loads(line) for line in open(f"{run_dir}/listen.jsonl")]
    cloud = {}
    for x in rows:
        if x["k"] == "cloud":
            cloud.setdefault(round(x["stamp"], 4), x["t"])
    if not cloud:
        return []
    t0 = min(cloud.values())
    out = []
    for x in rows:
        if x["k"] != "status":
            continue
        s = json.loads(x["v"])
        k = round(s["stamp"], 4) if s.get("stamp") else None
        if k in cloud and cloud[k] - t0 < window:
            out.append((x["t"] - cloud[k]) * 1e3)
    return out


def main(runs, stamps_path):
    per_run = []
    for name in sorted(os.listdir(runs)):
        d = os.path.join(runs, name)
        if not os.path.exists(os.path.join(d, "run.json")):
            continue
        image, rest = name.split("_", 1)
        bag = "roundT_doubleT" if rest.startswith("clear") else "doubleT_obstacle"
        a = analyze(d, bag, stamps_path)
        f3 = first_seconds(d, bag, stamps_path)
        per_run.append({"run": name, "image": image, "condition": rest.rstrip("0123456789"),
                        "frames_with_result": a["frames_with_result"], "decisions": a["counts"],
                        "first_stop_frame": a["first_stop_frame"],
                        "first_stop_after_first_cloud_s": a["first_stop_after_first_cloud_s"],
                        "stop_distance_m": a["stop_dist"],
                        "non_stop_after_first_stop": [r[:2] for r in a["non_stop_runs_after_first_stop"]],
                        "e2e_first3s_p50_ms": round(float(np.percentile(f3, 50)), 1) if f3 else None,
                        "e2e_first3s_p95_ms": round(float(np.percentile(f3, 95)), 1) if f3 else None,
                        "e2e_all_p95_ms": a["e2e_p95"], "e2e_current_p95_ms": a["e2e_cur_p95"],
                        "decode_detect_p95_ms": a["node_lat_p95"], "cpu_cores": a["cpu_cores"],
                        "rss_peak_mb": a["rss_mb"]})
    by = {}
    for r in per_run:
        by.setdefault((r["condition"], r["image"]), []).append(r)
    table = []
    for (cond, image), rs in sorted(by.items()):
        def rng(key):
            v = [r[key] for r in rs if r[key] is not None]
            return [min(v), max(v)] if v else None
        table.append({"condition": cond, "image": image, "runs": len(rs),
                      **{k: rng(k) for k in ("e2e_first3s_p50_ms", "e2e_first3s_p95_ms", "e2e_all_p95_ms",
                                             "e2e_current_p95_ms", "first_stop_after_first_cloud_s",
                                             "frames_with_result", "decode_detect_p95_ms")}})
    print(json.dumps({"conditions": table, "runs": per_run}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
