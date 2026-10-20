"""Run any replay script (runpy, unchanged) with the read-only switch hooks of falcon_switch_trace.py, recording
EVERY matched track per frame (not only those with switch state). For the A-axis probe (range_test.py):

    RESENSE_REPO=<tree> python hooks_runpy.py <out.ndjson> <script.py> <script args...>

With P4_DUMP="i,j" (call indices) and P4_DUMP_DIR the processed cloud of those calls is saved.

Per Detector.process call: index, the clusters with collision_core set, and per matched track: id, hits,
reported, last cluster (distance, lateral, zone, reason, height span, core), column hits / hold, core hits /
ready, cable kind / hits, and the tracker's own _qualifies with R3 on and off.
"""
import copy
import json
import os
import runpy
import sys
from types import SimpleNamespace

ROOT = os.environ["RESENSE_REPO"]
sys.path.insert(0, ROOT)
import resense.detector as detm  # noqa: E402
import resense.tracking as trk  # noqa: E402

rec = open(sys.argv[1], "w")
proc, fc, upd = detm.Detector.process, detm.find_clusters, trk.Tracker.update
st = {"i": -1, "cores": [], "clusters": []}


def r3(v):
    return round(float(v), 3)


DUMP = {int(v) for v in os.environ.get("P4_DUMP", "").split(",") if v}
DUMP_DIR = os.environ.get("P4_DUMP_DIR", ".")


def process(self, frame, *a, **k):
    st["i"] += 1
    st["cores"], st["clusters"] = [], []
    res = proc(self, frame, *a, **k)
    if st["i"] in DUMP:          # read-only: the processed cloud, lateral / height, each track's own cluster points
        import numpy as np
        dy, h = (np.asarray(v) for v in self._frame_hd)
        own = {f"own_{t.id}": t.last.points_idx for t in self.tracker.tracks if t.misses == 0 and t.last is not None}
        np.savez_compressed(os.path.join(DUMP_DIR, f"call{st['i']:05d}.npz"), xyz=np.asarray(self._frame_xyz, np.float32),
                            dy=dy.astype(np.float32), h=h.astype(np.float32), **own)
    return res


def find_clusters(*a, **k):
    res = fc(*a, **k)
    for c in res:
        row = {"d": r3(c.distance), "lat": r3(c.lateral), "h": r3(c.height_max - c.height_min),
               "size": [r3(v) for v in c.size], "zone": c.zone, "reason": c.reason, "n_gauge": int(c.n_gauge),
               "core": bool(getattr(c, "collision_core", False))}
        st["clusters"].append(row)
    return res


def update(self, *a, **k):
    res = upd(self, *a, **k)
    c = self.cfg
    other = copy.deepcopy(c)
    other.cable_confirm_time_s = 0.0 if c.cable_confirm_time_s > 0 else 0.3
    ns = SimpleNamespace(cfg=other, _timed=self._timed)
    tr = []
    for t in self.tracks:
        if t.misses or t.last is None:
            continue
        colsum = int(sum(t.column_hist))
        tr.append({"id": int(t.id), "d": r3(t.last.distance), "lat": r3(t.last.lateral), "hits": int(t.hits),
                   "reported": bool(t.reported), "zone": t.last.zone, "reason": t.last.reason,
                   "h": r3(t.last.height_max - t.last.height_min),
                   "core": bool(getattr(t.last, "collision_core", False)),
                   "col_hits": colsum, "column_hist": [bool(v) for v in t.column_hist],
                   "column_hold": int(t.column_hold), "core_hits": int(t.collision_core_hits),
                   "core_ready": bool(t.collision_core_ready), "cable_kind": int(t.cable_kind),
                   "cable_hits": int(t.cable_hits), "q_run": bool(trk.Tracker._qualifies(self, t)),
                   "q_other": bool(trk.Tracker._qualifies(ns, t))})
    rec.write(json.dumps({"i": st["i"], "clusters": st["clusters"], "tracks": tr}) + "\n")
    return res


detm.Detector.process, detm.find_clusters, trk.Tracker.update = process, find_clusters, update
sys.argv = sys.argv[2:]
try:
    runpy.run_path(sys.argv[0], run_name="__main__")
except SystemExit:
    pass
rec.close()
