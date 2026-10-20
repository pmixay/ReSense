"""Falcon with the switch trace: falcon_trace.py (unchanged, run through runpy) with resense.detector.find_clusters
and resense.tracking.Tracker.update wrapped read-only, as switch_trace.py does for the gate. Per frame it writes
<out>.switch.ndjson: the clusters with H1's collision_core set, and every matched track that has R3 state
(cable_kind / cable hits) or H1 state (core hits), or for which R3's fast path changes the tracker's own
_qualifies verdict (q_run != q_other), or the core suspends the column hold.
The run's .jsonl must equal a plain run's.

    RESENSE_REPO=<tree> python falcon_switch_trace.py <src> --out <prefix> [--set k=v]
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

out = sys.argv[sys.argv.index("--out") + 1]
rec = open(out + ".switch.ndjson", "w")
proc, fc, upd = detm.Detector.process, detm.find_clusters, trk.Tracker.update
st = {"i": -1, "cores": []}


def r3(v):
    return round(float(v), 3)


def process(self, frame, *a, **k):
    st["i"] += 1
    st["cores"] = []
    return proc(self, frame, *a, **k)


def find_clusters(*a, **k):
    res = fc(*a, **k)
    st["cores"] += [{"d": r3(c.distance), "lat": r3(c.lateral), "size": [r3(v) for v in c.size],
                     "h": r3(c.height_max - c.height_min), "zone": c.zone, "reason": c.reason}
                    for c in res if getattr(c, "collision_core", False)]
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
        q, qo = trk.Tracker._qualifies(self, t), trk.Tracker._qualifies(ns, t)
        colsum = sum(t.column_hist)
        hold_core = t.column_hold > 0 and colsum >= t.column_hold and not t.collision_core_ready
        hold_nocore = t.column_hold > 0 and colsum >= t.column_hold
        if q != qo or hold_core != hold_nocore or t.cable_kind or t.collision_core_hits:
            tr.append({"id": int(t.id), "d": r3(t.last.distance), "lat": r3(t.last.lateral), "hits": int(t.hits),
                       "reported": bool(t.reported), "cable_kind": int(t.cable_kind),
                       "cable_hits": int(t.cable_hits), "q_run": bool(q), "q_other": bool(qo),
                       "core_hits": int(t.collision_core_hits), "core_ready": bool(t.collision_core_ready),
                       "hold_core": bool(hold_core), "hold_nocore": bool(hold_nocore)})
    if st["cores"] or tr:
        rec.write(json.dumps({"i": st["i"], "cores": st["cores"], "tracks": tr}) + "\n")
        rec.flush()
    return res


detm.Detector.process, detm.find_clusters, trk.Tracker.update = process, find_clusters, update
sys.argv = [os.path.join(ROOT, "docs/evidence/f1_false_alarms_2026-10-19/scripts/falcon_trace.py")] + sys.argv[1:]
try:
    runpy.run_path(sys.argv[0], run_name="__main__")
except SystemExit:
    pass
rec.close()
