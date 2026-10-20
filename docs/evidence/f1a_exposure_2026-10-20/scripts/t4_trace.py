"""T4 (P4 handoff 20.10): which low clusters does F1a make weak on set O and the ride, and are they real objects?

Runs the regression gate's own replay (``eval_real.run_piece``: the gate's cache files, pieces, stamps and config) on
``cloud_with_fake_obj`` and the ride's 8 pieces, with ``Detector._rail_reference`` wrapped read-only: after the
original returns, every cluster it added to ``_low_height`` this frame (F1a: kind ``low``, top below the frame's own
rail-line reference + ``local_rail_margin``) is recorded with its top, the reference (``lowobj.local_rail_reference``
on the same returns as the detector), its distance, lateral, size and voxels, and the returns within 6 m along and
2.5 m across it are saved (detector frame, ``dy``, ``h``, the cluster's own indices) for pictures. Each piece's
``.jsonl`` must equal the plain gate run's (checked by the caller with cmp_frames.py).

    RESENSE_REPO=<tree> python t4_trace.py <cache dir> <out dir> [--jobs 3] [--names cloud_with_fake_obj,new_data]
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


def worker(job):
    import resense.detector as detm
    from resense import lowobj
    import eval_real
    name, files, cfg_dict, out_path, stamps, speeds = job
    rec = open(out_path.replace(".jsonl", ".f1a.jsonl"), "w")
    dump_dir = out_path.replace(".jsonl", "_f1a")
    os.makedirs(dump_dir, exist_ok=True)
    proc, rail = detm.Detector.process, detm.Detector._rail_reference
    state = {"stem": None}

    def process(self, frame, *a, **k):
        state["stem"] = frame.frame_id
        return proc(self, frame, *a, **k)

    def rail_reference(self, clusters, xyz, dy_rail, h_all):
        before = list(self._low_height)
        out = rail(self, clusters, xyz, dy_rail, h_all)
        new = [c for c in self._low_height if not any(c is b for b in before)]
        if new:
            low = self.cfg.lowobj
            free = (lowobj.low_free_mask(xyz.shape[0], clusters + before) if low.local_rail_exclude_low else None)
            Xr, dyr, hr = (xyz[:, 0], dy_rail, h_all) if free is None else (xyz[free, 0], dy_rail[free], h_all[free])
            for k, c in enumerate(new):
                ref = lowobj.local_rail_reference(c, Xr, dyr, hr, low, self.cfg.track.rails_spacing)
                r = {"stem": state["stem"], "k": k, "d": round(float(c.distance), 2), "lat": round(float(c.lateral), 3),
                     "top": round(float(c.height_max), 3), "hmin": round(float(c.height_min), 3),
                     "ref": None if ref is None else round(float(ref), 3), "size": [round(float(v), 3) for v in c.size],
                     "n": int(c.n), "n_gauge": int(c.n_gauge), "centroid": [round(float(v), 3) for v in c.centroid]}
                rec.write(json.dumps(r) + "\n")
                x0, x1 = float(c.bbox_min[0]) - 6.0, float(c.bbox_max[0]) + 6.0
                m = (xyz[:, 0] > x0) & (xyz[:, 0] < x1) & (np.abs(xyz[:, 1] - float(c.centroid[1])) < 2.5)
                idx = np.flatnonzero(m)
                own = np.isin(idx, c.points_idx)
                np.savez_compressed(os.path.join(dump_dir, f"{state['stem']}_{k}.npz"), xyz=xyz[idx].astype(np.float32),
                                    dy=np.asarray(dy_rail)[idx].astype(np.float32), h=np.asarray(h_all)[idx].astype(np.float32),
                                    own=own)
        return out

    detm.Detector.process = process
    detm.Detector._rail_reference = rail_reference
    try:
        return eval_real.run_piece(job)
    finally:
        rec.close()
        detm.Detector.process, detm.Detector._rail_reference = proc, rail   # a reused worker must not stack wrappers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("out")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--names", default="cloud_with_fake_obj,new_data")
    ap.add_argument("--chunks", type=int, default=8)
    a = ap.parse_args()
    import eval_real
    from scripts.cache_io import cache_files, load_cache_stamps
    os.makedirs(a.out, exist_ok=True)
    cfg_dict = eval_real.load_cfg_dict(os.path.join(ROOT, "configs", "default.yaml"), [])
    jobs = []
    for name in a.names.split(","):
        d = os.path.join(a.cache, name)
        files = cache_files(d)
        stamps = load_cache_stamps(d)
        n = a.chunks if name == "new_data" else 1
        for k, part in enumerate(np.array_split(np.array(files), n)):
            out = os.path.join(a.out, f"{name}.jsonl" if n == 1 else f"{name}_{k}.jsonl")
            jobs.append((name, list(part), cfg_dict, out, stamps, None))
    jobs.sort(key=lambda j: -len(j[1]))
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for name, path, _ in ex.map(worker, jobs):
            print("done", name, path, flush=True)


if __name__ == "__main__":
    main()
