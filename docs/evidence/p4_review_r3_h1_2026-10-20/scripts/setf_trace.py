"""Set F straight (the gate's own arguments and ``far_range_eval.py`` unchanged, imported as a module) under the
read-only switch hooks: ``run_sequence`` is wrapped to tag the job (kind, first file), ``Detector.process`` to tag
the frame, ``Tracker.update`` to record every matched track after it (R3 state, the tracker's own ``_qualifies`` with
R3 on and off, H1 state). Workers inherit the patches by fork; each writes ``<out>.<pid>.ndjson``. The report written
by far_range_eval itself (``--out``) must equal the plain run's (checked by the caller).

    RESENSE_REPO=<tree> python setf_trace.py <out prefix> <report.json> [--set k=v]
"""
import copy
import json
import os
import sys
from types import SimpleNamespace

ROOT = os.environ["RESENSE_REPO"]
for p in (ROOT, os.path.join(ROOT, "scripts")):
    sys.path.insert(0, p)
import resense.detector as detm  # noqa: E402
import resense.tracking as trk  # noqa: E402
import far_range_eval as fre  # noqa: E402

prefix, report = sys.argv[1], sys.argv[2]
extra = sys.argv[3:]
state = {"job": None, "frame": None, "fh": None}
proc, upd, run_seq = detm.Detector.process, trk.Tracker.update, fre.run_sequence


def fh():
    if state["fh"] is None:
        state["fh"] = open(f"{prefix}.{os.getpid()}.ndjson", "a")
    return state["fh"]


def run_sequence(job):
    state["job"] = (job[3], os.path.basename(str(job[0][0])))      # kind, first cache file
    return run_seq(job)


run_sequence.__module__, run_sequence.__qualname__ = run_seq.__module__, run_seq.__qualname__


def process(self, frame, *a, **k):
    state["frame"] = frame.frame_id
    return proc(self, frame, *a, **k)


def update(self, *a, **k):
    res = upd(self, *a, **k)
    c = self.cfg
    other = copy.deepcopy(c)
    other.cable_confirm_time_s = 0.0 if c.cable_confirm_time_s > 0 else 0.3
    ns = SimpleNamespace(cfg=other, _timed=self._timed)
    rows = []
    for t in self.tracks:
        if t.misses or t.last is None:
            continue
        q, qo = trk.Tracker._qualifies(self, t), trk.Tracker._qualifies(ns, t)
        if q != qo or t.cable_kind or t.collision_core_hits:
            lc = t.last
            rows.append({"id": int(t.id), "hits": int(t.hits), "reported": bool(t.reported), "d": round(float(lc.distance), 2),
                         "lat": round(float(lc.lateral), 3), "kind": lc.kind, "zone": lc.zone, "reason": lc.reason,
                         "n_raw": int(lc.n_raw), "n_pts": int(len(lc.points_idx)), "cable_kind": int(t.cable_kind),
                         "cable_hits": int(t.cable_hits), "cable_span": round(float(t.cable_span_s), 3),
                         "q_run": bool(q), "q_other": bool(qo), "core_hits": int(t.collision_core_hits)})
    if rows:
        fh().write(json.dumps({"job": state["job"], "frame": state["frame"], "tracks": rows}) + "\n")
        fh().flush()
    return res


detm.Detector.process, trk.Tracker.update, fre.run_sequence = process, update, run_sequence
from regression_gate import SET_F_STRAIGHT  # noqa: E402

CACHE = os.environ.get("P4_CACHE", "/home/user/data/cache")
sys.argv = ["far_range_eval.py", *[f"--{k}={v}" for k, v in SET_F_STRAIGHT.items()],
            "--cache", os.path.join(CACHE, "new_data"), "--config", os.path.join(ROOT, "configs/default.yaml"),
            "--jobs", "4", "--out", report, *extra]
fre.main()
