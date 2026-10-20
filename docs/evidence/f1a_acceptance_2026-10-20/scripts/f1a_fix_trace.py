"""F1a fix acceptance (P4, 20.10): which part of P3's repair (``f07f4b8``) lets a low cluster through that the old rule
made weak, and where.

Runs the regression gate's own replay (``eval_real.run_piece``: the gate's cache files, pieces, stamps and config) with
``resense.detector.rail_reference_check`` wrapped read-only. After the original returns, every cluster it checks (kind
``low``, zone gauge, no reason, not weak, with points) is recomputed from the same arrays on four rules:

* A, the old rule (``8c2bf51``): top = ``height_max``, reference = ``local_rail_reference`` on every return;
* B, the new top only: top = max(``height_max``, the highest return in the cluster's footprint below
  ``foot_max_top``), the old reference;
* C, the new reference only: the old top, reference = min(the reference on the returns ``free`` leaves, the old one),
  none if either is missing (only with ``free``, i.e. ``local_rail_exclude_low``);
* D, the new rule: the new top and the new reference (without ``free``: the new top and the old reference).

A rule rejects (makes the cluster weak) when its reference exists and top < reference + ``local_rail_margin``. The
rule of the tree (D with ``free`` and a footprint top, else A) must equal what the detector returned for every
cluster (``match``). A cluster A rejects and D does not is a flip; its cause is ``top`` (B passes, C still rejects),
``reference`` (C passes, B still rejects), ``either`` (both pass) or ``joint`` (both still reject). Recorded per
checked cluster: frame stem, distance, lateral, size, centroid, bbox, the tops, the references, A-D, the detector's
verdict; for flips and A-rejected clusters, the returns within 6 m along and 2.5 m across are saved (detector frame,
``dy``, ``h``, own indices, footprint) for pictures. ``Tracker.update`` is wrapped read-only too: after it, every
track matched in the frame (``misses`` 0) is recorded with its id (the output detection id), hits, age, whether it is
reported, its last cluster's zone, kind and centroid, and, when that cluster is one of the frame's checked clusters,
its index and A / D / cause (the track's lineage: which of its hits the old rule would have made weak). Each piece's
``.jsonl`` must equal the plain gate run's (checked by the caller with cmp_frames.py).

    RESENSE_REPO=<tree> python f1a_fix_trace.py <cache dir> <out dir> [--jobs 2] [--names doubleT_platform,new_data]
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
    import resense.tracking as trk
    from resense import lowobj
    import eval_real
    name, files, cfg_dict, out_path, stamps, speeds = job
    rec = open(out_path.replace(".jsonl", ".fix.ndjson"), "w")
    trec = open(out_path.replace(".jsonl", ".tracks.ndjson"), "w")
    dump_dir = out_path.replace(".jsonl", "_fix")
    os.makedirs(dump_dir, exist_ok=True)
    proc, check, upd = detm.Detector.process, detm.rail_reference_check, trk.Tracker.update
    state = {"stem": None, "tags": {}}

    def process(self, frame, *a, **k):
        state["stem"], state["tags"] = frame.frame_id, {}
        return proc(self, frame, *a, **k)

    def update(self, *a, **k):
        out = upd(self, *a, **k)
        rows = []
        for t in self.tracks:
            if t.misses == 0 and t.last is not None:
                tag = state["tags"].get(id(t.last))
                tag = tag if tag is not None and tag[0] is t.last else None
                rows.append([int(t.id), int(t.hits), int(t.age), bool(t.reported), t.last.zone, t.last.kind,
                             [r3(t.last.centroid[0]), r3(t.last.centroid[1])], None if tag is None else list(tag[1:])])
        trec.write(json.dumps({"stem": state["stem"], "tracks": rows}) + "\n")
        return out

    def rail_reference_check(clusters, X, dy, h, cfg, rails_spacing, free=None):
        out = check(clusters, X, dy, h, cfg, rails_spacing, free)
        if not cfg.local_rail_margin > 0:
            return out
        m = float(cfg.local_rail_margin)
        fixed = "footprint" in lowobj.rail_reference_check.__code__.co_varnames
        foot_top = float(getattr(cfg, "foot_max_top", np.inf))
        for k, c in enumerate(clusters):
            if c.kind != "low" or c.zone != "gauge" or c.reason or c.low_height_weak or not c.points_idx.size:
                continue
            top_old = float(c.height_max)
            d = dy[c.points_idx]
            fp = ((X >= c.bbox_min[0]) & (X <= c.bbox_max[0]) & (dy >= d.min()) & (dy <= d.max()) & (h < foot_top))
            top_new = max(top_old, float(h[fp].max())) if fp.any() else top_old
            ref_orig = lowobj.local_rail_reference(c, X, dy, h, cfg, rails_spacing)
            ref_ind = (lowobj.local_rail_reference(c, X[free], dy[free], h[free], cfg, rails_spacing)
                       if free is not None else None)
            ref_new = (min(ref_ind, ref_orig) if ref_ind is not None and ref_orig is not None else None)
            rej = lambda top, ref: ref is not None and top < ref + m  # noqa: E731
            A, B = rej(top_old, ref_orig), rej(top_new, ref_orig)
            C = rej(top_old, ref_new) if free is not None else A
            D = rej(top_new, ref_new if free is not None else ref_orig)
            tree_rule = D if fixed else A
            actual = any(c is o for o in out)
            cause = None
            if A and not D:
                cause = {(False, True): "top", (True, False): "reference", (False, False): "either",
                         (True, True): "joint"}[(B, C)]
            r = {"stem": state["stem"], "k": k, "d": r3(c.distance), "lat": r3(c.lateral),
                 "size": [r3(v) for v in c.size], "centroid": [r3(v) for v in c.centroid],
                 "bbox": [[r3(v) for v in c.bbox_min], [r3(v) for v in c.bbox_max]], "n": int(c.n),
                 "top_old": r3(top_old), "top_new": r3(top_new), "ref_orig": r3(ref_orig), "ref_ind": r3(ref_ind),
                 "free": free is not None, "fixed_code": fixed, "A": A, "B": B, "C": C, "D": D, "actual": actual,
                 "match": actual == tree_rule, "cause": cause}
            rec.write(json.dumps(r) + "\n")
            state["tags"][id(c)] = (c, k, A, D, cause)
            if A or D or actual:
                x0, x1 = float(c.bbox_min[0]) - 6.0, float(c.bbox_max[0]) + 6.0
                sel = (X > x0) & (X < x1) & (np.abs(dy - float(np.median(d))) < 2.5)
                idx = np.flatnonzero(sel)
                np.savez_compressed(os.path.join(dump_dir, f"{state['stem']}_{k}.npz"), X=X[idx].astype(np.float32),
                                    dy=dy[idx].astype(np.float32), h=h[idx].astype(np.float32),
                                    own=np.isin(idx, c.points_idx), fp=fp[idx],
                                    free=(free[idx] if free is not None else np.ones(idx.size, bool)))
        return out

    detm.Detector.process = process
    detm.rail_reference_check = rail_reference_check
    trk.Tracker.update = update
    try:
        return eval_real.run_piece(job)
    finally:
        rec.close()
        trec.close()
        # a reused worker must not stack wrappers
        detm.Detector.process, detm.rail_reference_check, trk.Tracker.update = proc, check, upd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("out")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--names", default="doubleT_platform,cloud_with_fake_obj,new_data")
    ap.add_argument("--chunks", type=int, default=8)
    ap.add_argument("--pieces", default="", help="ride pieces to run, e.g. 1,4,7 (default all)")
    a = ap.parse_args()
    import eval_real
    from scripts.cache_io import cache_files, load_cache_stamps
    os.makedirs(a.out, exist_ok=True)
    cfg_dict = eval_real.load_cfg_dict(os.path.join(ROOT, "configs", "default.yaml"), [])
    pieces = {int(v) for v in a.pieces.split(",") if v}
    jobs = []
    for name in a.names.split(","):
        d = os.path.join(a.cache, name)
        files = cache_files(d)
        stamps = load_cache_stamps(d)
        n = a.chunks if name == "new_data" else 1
        for k, part in enumerate(np.array_split(np.array(files), n)):
            if n > 1 and pieces and k not in pieces:
                continue
            out = os.path.join(a.out, f"{name}.jsonl" if n == 1 else f"{name}_{k}.jsonl")
            jobs.append((name, list(part), cfg_dict, out, stamps, None))
    jobs.sort(key=lambda j: -len(j[1]))
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for name, path, _ in ex.map(worker, jobs):
            print("done", name, path, flush=True)


if __name__ == "__main__":
    main()
