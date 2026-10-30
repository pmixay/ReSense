#!/usr/bin/env python3
"""The gate's own per-frame machinery (scripts/regression_gate.py ``measure``: a fresh detector per recording, the ride in
8 pieces, cached receive stamps, no speed, default config + --set) with one addition: after each frame the clear-distance rule
that fired (``HealthMonitor.last_clear_rule``) is written next to the frame's clear distance. Output per piece:
``<out>/<name>[_k].jsonl`` with {frame, clear, rule, obstacle, lock_lost_message}. Nothing is changed in the detector; the
gate's rows of the same configuration must carry the same clear in every row (compare_gate_rows.py checks it).

    RESENSE_REPO=<tree> run_cache_trace.py --cache /data/cache --out DIR [--set k=v ...] [--jobs 4] [--only name,...]
"""
import argparse, glob, json, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(os.environ["RESENSE_REPO"]).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
import resense  # noqa: E402
assert Path(resense.__file__).resolve().is_relative_to(ROOT), resense.__file__
from scripts import eval_real  # noqa: E402
from scripts.cache_io import cache_files, load_cache_stamps  # noqa: E402

RIDE, SET_O = "new_data", "cloud_with_fake_obj"


def bed_excess(det):
    """Read-only: the largest excess of |model rail head - mount plane| over the H' tolerance (cluster.mount_cross_tol +
    mount_cross_grade * X) at X = 5, 10, ..., 30 m (H' range); None without a final mount calibration."""
    st = det.calib.state
    if st.height is None or st.status not in ("ok", "identity") or not np.isfinite(st.height):
        return None
    xs = np.arange(5.0, 30.01, 5.0)
    cc = det.cfg.cluster
    return round(float((np.abs(np.asarray(det.track.rail_z(xs)) + float(st.height)) - (cc.mount_cross_tol + cc.mount_cross_grade * xs)).max()), 3)


def piece(job):
    name, files, cfg_dict, out, stamps = job
    sys.path.insert(0, os.getcwd())
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    from scripts.cache_io import cache_file_stem, load_cache_array
    cfg = DetectorConfig.from_dict(cfg_dict)
    det = Detector(cfg)
    with open(out, "w", encoding="utf-8") as fh:
        for i, f in enumerate(files):
            stem = cache_file_stem(f)
            idx = int(stem.rsplit("_", 1)[1])
            fr = frame_from_compact(load_cache_array(f), cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
            res = det.process(fr)
            fh.write(json.dumps({"frame": idx if name in eval_real.SIX else i, "clear": float(res.clear_distance),
                                 "rule": det.health.last_clear_rule, "obstacle": bool(res.obstacle),
                                 "lost_msg": any("track model on its prior" in m for m in res.health["messages"]),
                                 "bed_excess": bed_excess(det), "rail_score": float(res.track.rail_score)}) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--config", default=str(ROOT / "configs/default.yaml"))
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--chunks", type=int, default=8)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cfg_dict = eval_real.load_cfg_dict(a.config, a.set)
    names = [n for n in eval_real.SIX + [SET_O, RIDE] if not a.only or n in a.only.split(",")]
    jobs = []
    for name in names:
        d = os.path.join(a.cache, name)
        files = cache_files(d)
        if not files:
            continue
        stamps = load_cache_stamps(d)
        n = a.chunks if name == RIDE else 1
        for k, part in enumerate(np.array_split(np.array(files), n)):
            jobs.append((name, list(part), cfg_dict, os.path.join(a.out, f"{name}.jsonl" if n == 1 else f"{name}_{k}.jsonl"), stamps))
    jobs.sort(key=lambda j: -len(j[1]))
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for out in ex.map(piece, jobs):
            print("done", out, flush=True)
    json.dump({"repo": str(ROOT), "resense_file": resense.__file__, "set": a.set, "config": a.config}, open(os.path.join(a.out, "meta.json"), "w"))


if __name__ == "__main__":
    main()
