"""Which low clusters the F1a completion's new branch (``lowobj._rail_surface_reference``, a77d884) rejects (P4, 20.10).

The regression gate's own replay (``eval_real.run_piece``: its cache files, pieces, stamps, shipped config) with
``lowobj._rail_surface_reference`` and ``detector.rail_reference_check`` wrapped read-only. For every cluster of
a frame that reaches the new branch's call, recorded: frame stem, distance, lateral, size, the cluster's own
``height_max``, the footprint top, the first rule's reference (``original``, ``ref``), the surface the branch
returned (None = fails open) and whether the cluster ends up rejected, and by which rule. The decisive branch is
recomputed independently from the same arrays (the first rule, then the surface rule) and compared with what the
detector returned (``match``); a frame whose first rule rejects never reaches the new branch. ``Tracker.update`` is
wrapped read-only too: every track matched in the frame is written with its id, hits, age, reported flag, last
cluster zone / kind / centroid. Each piece's ``.jsonl`` must equal the plain gate run's (``cmp_frames.py``).

    RESENSE_REPO=<tree> python surface_trace.py <cache dir> <out dir> [--jobs 3] [--names a,b] [--pieces 1,4]
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
    import eval_real
    import resense.detector as detm
    import resense.tracking as trk
    from resense import lowobj
    name, files, cfg_dict, out_path, stamps, speeds = job
    rec = open(out_path.replace(".jsonl", ".surface.ndjson"), "w")
    trec = open(out_path.replace(".jsonl", ".tracks.ndjson"), "w")
    proc, check, upd, surf = detm.Detector.process, detm.rail_reference_check, trk.Tracker.update, lowobj._rail_surface_reference
    state = {"stem": None, "calls": {}}

    def process(self, frame, *a, **k):
        state["stem"], state["calls"] = frame.frame_id, {}
        return proc(self, frame, *a, **k)

    def surface(c, X, dy, h, d0, d1, cfg, rails_spacing):
        out = surf(c, X, dy, h, d0, d1, cfg, rails_spacing)
        state["calls"][id(c)] = out
        return out

    def update(self, *a, **k):
        out = upd(self, *a, **k)
        rows = [[int(t.id), int(t.hits), int(t.age), bool(t.reported), t.last.zone, t.last.kind,
                 [r3(t.last.centroid[0]), r3(t.last.centroid[1])]]
                for t in self.tracks if t.misses == 0 and t.last is not None]
        trec.write(json.dumps({"stem": state["stem"], "tracks": rows}) + "\n")
        return out

    def rail_reference_check(clusters, X, dy, h, cfg, rails_spacing, free=None):
        state["calls"] = {}
        out = check(clusters, X, dy, h, cfg, rails_spacing, free)
        if not cfg.local_rail_margin > 0 or free is None:
            return out
        m = float(cfg.local_rail_margin)
        Xr, dyr, hr = X[free], dy[free], h[free]
        for k, c in enumerate(clusters):
            if id(c) not in state["calls"]:
                continue
            d = dy[c.points_idx]
            fp = ((X >= c.bbox_min[0]) & (X <= c.bbox_max[0]) & (dy >= d.min()) & (dy <= d.max()) & (h < cfg.foot_max_top))
            top = max(float(c.height_max), float(h[fp].max())) if fp.any() else float(c.height_max)
            original = lowobj.local_rail_reference(c, X, dy, h, cfg, rails_spacing)
            ref = lowobj.local_rail_reference(c, Xr, dyr, hr, cfg, rails_spacing)
            ref = min(ref, original) if (ref is not None and original is not None) else None
            first = ref is not None and top < ref + m
            surface_v = state["calls"][id(c)]
            second = (not first) and original is not None and surface_v is not None \
                and top <= surface_v + float(cfg.rail_start_margin)
            actual = any(c is o for o in out)
            rec.write(json.dumps({
                "stem": state["stem"], "k": k, "d": r3(c.distance), "lat": r3(c.lateral),
                "size": [r3(v) for v in c.size], "n": int(c.n), "height_max": r3(c.height_max), "top": r3(top),
                "original": r3(original), "ref": r3(ref), "surface": r3(surface_v), "first_rule": bool(first),
                "surface_rule": bool(second), "rejected": bool(actual), "match": bool(actual == (first or second))}) + "\n")
        return out

    detm.Detector.process = process
    detm.rail_reference_check = rail_reference_check
    lowobj._rail_surface_reference = surface
    trk.Tracker.update = update
    try:
        return eval_real.run_piece(job)
    finally:
        rec.close()
        trec.close()
        detm.Detector.process, detm.rail_reference_check, trk.Tracker.update = proc, check, upd
        lowobj._rail_surface_reference = surf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("out")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--names", default="doubleT_obstacle,doubleT_platform,cloud_with_fake_obj,new_data")
    ap.add_argument("--chunks", type=int, default=8)
    ap.add_argument("--pieces", default="")
    a = ap.parse_args()
    import eval_real
    from scripts.cache_io import cache_files, load_cache_stamps
    os.makedirs(a.out, exist_ok=True)
    cfg_dict = eval_real.load_cfg_dict(os.path.join(ROOT, "configs", "default.yaml"), [])
    pieces = {int(v) for v in a.pieces.split(",") if v}
    jobs = []
    for name in a.names.split(","):
        d = os.path.join(a.cache, name)
        files, stamps = cache_files(d), load_cache_stamps(d)
        n = a.chunks if name == "new_data" else 1
        for k, part in enumerate(np.array_split(np.array(files), n)):
            if n > 1 and pieces and k not in pieces:
                continue
            jobs.append((name, list(part), cfg_dict, os.path.join(a.out, f"{name}.jsonl" if n == 1 else f"{name}_{k}.jsonl"),
                         stamps, None))
    jobs.sort(key=lambda j: -len(j[1]))
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for name, path, _ in ex.map(worker, jobs):
            print("done", name, path, flush=True)


if __name__ == "__main__":
    main()
