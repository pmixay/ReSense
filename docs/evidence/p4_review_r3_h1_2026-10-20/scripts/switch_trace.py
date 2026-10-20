"""Read-only trace of the two switches under review (P4, 20.10) on the regression gate's own replay
(``eval_real.run_piece``: the gate's cache files, ride pieces, stamps and config, ``--set`` overrides applied
exactly as regression_gate.py does).

Wrapped, each original called first and its result returned unchanged:

* ``resense.detector.find_clusters`` (the name the detector calls): every returned cluster whose
  ``collision_core`` (H1) is set is recorded: frame stem, distance, lateral, size, height span, zone, reason,
  kind, voxels, strict-gauge voxels, current/total points;
* ``resense.tracking.Tracker.update``: after it, every track matched in the frame (``misses`` 0) is recorded:
  id (= the output detection id), hits, age, reported, span, its last cluster (zone, kind, reason, distance,
  lateral, size, height span, n_raw vs points, collision_core), R3 state (``cable_kind``, ``cable_hits``,
  ``cable_span_s``) and H1 state (``collision_core_hits`` / ``_ready``, column hits in ``column_hist``,
  ``column_hold``), plus two verdicts recomputed by calling the tracker's own ``_qualifies`` (a pure function
  of the track and the config) with the run's config and with the other R3 setting (``q_r3_on`` / ``q_r3_off``),
  and the column-hold verdict with and without the core (``hold_core`` / ``hold_nocore``). Which rule fired is
  thus recorded, not reconstructed.

Each piece's ``.jsonl`` must equal the plain gate run's (checked with cmp_frames.py).

    RESENSE_REPO=<tree> python switch_trace.py <cache> <out> [--set k=v] [--names a,b] [--pieces 1,4] [--jobs 2]
"""
import argparse
import copy
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from types import SimpleNamespace

import numpy as np

ROOT = os.environ["RESENSE_REPO"]
for p in (ROOT, os.path.join(ROOT, "scripts")):
    sys.path.insert(0, p)


def r3(v):
    return None if v is None else round(float(v), 3)


def cl_row(c):
    return {"d": r3(c.distance), "lat": r3(c.lateral), "size": [r3(v) for v in c.size],
            "hmin": r3(c.height_min), "hmax": r3(c.height_max), "zone": c.zone, "reason": c.reason, "kind": c.kind,
            "n": int(c.n), "n_gauge": int(c.n_gauge), "n_raw": int(c.n_raw), "n_pts": int(len(c.points_idx)),
            "core": bool(getattr(c, "collision_core", False)), "thin": bool(c.thin), "weak": bool(c.weak)}


def worker(job):
    import resense.detector as detm
    import resense.tracking as trk
    import eval_real
    name, files, cfg_dict, out_path, stamps, speeds = job
    trec = open(out_path.replace(".jsonl", ".trace.ndjson"), "w")
    proc, fc, upd = detm.Detector.process, detm.find_clusters, trk.Tracker.update
    state = {"stem": None, "cores": []}

    def process(self, frame, *a, **k):
        state["stem"], state["cores"] = frame.frame_id, []
        return proc(self, frame, *a, **k)

    def find_clusters(*a, **k):
        out = fc(*a, **k)
        state["cores"] += [cl_row(c) for c in out if getattr(c, "collision_core", False)]
        return out

    def update(self, *a, **k):
        out = upd(self, *a, **k)
        c = self.cfg
        other = copy.deepcopy(c)
        other.cable_confirm_time_s = 0.0 if c.cable_confirm_time_s > 0 else 0.3
        ns_other = SimpleNamespace(cfg=other, _timed=self._timed)
        rows = []
        for t in self.tracks:
            if t.misses != 0 or t.last is None:
                continue
            q_run = trk.Tracker._qualifies(self, t)
            q_other = trk.Tracker._qualifies(ns_other, t)
            on = c.cable_confirm_time_s > 0
            colsum = int(sum(t.column_hist))
            rows.append({"id": int(t.id), "hits": int(t.hits), "age": int(t.age), "reported": bool(t.reported),
                         "span": r3(t.span_s), "last": cl_row(t.last),
                         "cable_kind": int(t.cable_kind), "cable_hits": int(t.cable_hits),
                         "cable_span": r3(t.cable_span_s),
                         "q_r3_on": q_run if on else q_other, "q_r3_off": q_other if on else q_run,
                         "core_hits": int(t.collision_core_hits), "core_ready": bool(t.collision_core_ready),
                         "col_hits": colsum, "column_hold": int(t.column_hold),
                         "hold_core": bool(t.column_hold > 0 and colsum >= t.column_hold and not t.collision_core_ready),
                         "hold_nocore": bool(t.column_hold > 0 and colsum >= t.column_hold)})
        trec.write(json.dumps({"stem": state["stem"], "cores": state["cores"], "tracks": rows}) + "\n")
        return out

    detm.Detector.process, detm.find_clusters, trk.Tracker.update = process, find_clusters, update
    try:
        return eval_real.run_piece(job)
    finally:
        trec.close()
        detm.Detector.process, detm.find_clusters, trk.Tracker.update = proc, fc, upd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("out")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--names", default="")
    ap.add_argument("--chunks", type=int, default=8)
    ap.add_argument("--pieces", default="", help="ride pieces to run, e.g. 1,4,7 (default all)")
    a = ap.parse_args()
    import eval_real
    from scripts.cache_io import cache_files, load_cache_stamps
    os.makedirs(a.out, exist_ok=True)
    cfg_dict = eval_real.load_cfg_dict(os.path.join(ROOT, "configs", "default.yaml"), a.set)
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
