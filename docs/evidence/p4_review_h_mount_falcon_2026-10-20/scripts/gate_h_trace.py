"""H′ on the gate data (P4, 20.10): the regression gate's own replay (``eval_real.run_piece``: the gate's cache
files, pieces of the ride, stamps and the shipped config) with ``Detector._mount_cross_check`` wrapped read-only.
After the original returns, every cluster it looked at (zone gauge, no reason before the check, within
``mount_cross_range``, with points) is written to ``<piece>.h.ndjson``: distance, lateral, kind, the model rail
head ``track.rail_z(X)``, the mount plane, their disagreement against ``mount_cross_tol + mount_cross_grade * X``,
the cluster's heights above the plane and whether H′ made it advisory (``height_conflict``). Frames where the check
returns early (mount not final) are counted. Each piece's ``.jsonl`` must equal the plain gate run's
(``cmp_frames.py``) before the record is used.

    RESENSE_REPO=<tree> python gate_h_trace.py <cache dir> <out dir> [--jobs 3]
"""
import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ROOT = os.environ["RESENSE_REPO"]
for p in (ROOT, os.path.join(ROOT, "scripts")):
    sys.path.insert(0, p)


def r3(v):
    return None if v is None else round(float(v), 3)


def worker(job):
    import resense.detector as detm
    import eval_real
    name, files, cfg_dict, out_path, stamps, speeds = job
    rec = open(out_path.replace(".jsonl", ".h.ndjson"), "w")
    proc, check = detm.Detector.process, detm.Detector._mount_cross_check
    state = {"stem": None, "calls": 0}

    def process(self, frame, *a, **k):
        state["stem"], state["calls"] = frame.frame_id, 0
        out = proc(self, frame, *a, **k)
        if state["calls"] == 0:
            rec.write(json.dumps({"stem": state["stem"], "called": False}) + "\n")
        return out

    def mount_cross_check(self, clusters, xyz):
        before = [(c.zone, c.reason) for c in clusters]
        out = check(self, clusters, xyz)
        state["calls"] += 1
        cc, st = self.cfg.cluster, self.calib.state
        ok = st.height is not None and st.status in ("ok", "identity") and np.isfinite(st.height)
        rows = []
        if ok:
            plane = -float(st.height)
            top = float(np.asarray(self.cfg.gauge.profile, dtype=np.float64)[:, 1].max())
            for k, cl in enumerate(clusters):
                z0, r0 = before[k]
                if z0 != "gauge" or r0 or cl.distance > cc.mount_cross_range or not cl.points_idx.size:
                    continue
                x = float(cl.distance)
                rz = float(self.track.rail_z(x))
                hm = xyz[cl.points_idx, 2].astype(np.float64) - plane
                rows.append({"k": k, "d": r3(x), "lat": r3(cl.lateral), "kind": cl.kind, "n": int(cl.n),
                             "rail_z": r3(rz), "plane": r3(plane), "diff": r3(abs(rz - plane)),
                             "thr": r3(cc.mount_cross_tol + cc.mount_cross_grade * x),
                             "hm_min": r3(hm.min()), "hm_max": r3(hm.max()), "top": r3(top),
                             "demoted": cl.reason == "height_conflict"})
        rec.write(json.dumps({"stem": state["stem"], "called": True, "ok": bool(ok), "status": st.status,
                              "rows": rows}) + "\n")
        return out

    detm.Detector.process = process
    detm.Detector._mount_cross_check = mount_cross_check
    try:
        return eval_real.run_piece(job)
    finally:
        rec.close()
        detm.Detector.process, detm.Detector._mount_cross_check = proc, check


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("out")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--chunks", type=int, default=8)
    a = ap.parse_args()
    import eval_real
    from regression_gate import RIDE, SET_O, SIX
    from scripts.cache_io import cache_files, load_cache_stamps
    os.makedirs(a.out, exist_ok=True)
    cfg_dict = eval_real.load_cfg_dict(os.path.join(ROOT, "configs", "default.yaml"), [])
    jobs = []
    for name in SIX + [SET_O, RIDE]:
        d = os.path.join(a.cache, name)
        files = cache_files(d)
        stamps = load_cache_stamps(d)
        n = a.chunks if name == RIDE else 1
        for k, part in enumerate(np.array_split(np.array(files), n)):
            out = os.path.join(a.out, f"{name}.jsonl" if n == 1 else f"{name}_{k}.jsonl")
            jobs.append((name, list(part), cfg_dict, out, stamps, None))
    jobs.sort(key=lambda j: -len(j[1]))
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for name, path, _ in ex.map(worker, jobs):
            print("done", name, path, flush=True)


if __name__ == "__main__":
    main()
