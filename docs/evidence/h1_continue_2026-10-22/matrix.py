"""H1 synthetic physical matrix on the checkout in RESENSE_REPO (31 directed sequences, 518 scans).

The 31 sequences and their geometry are the ones of h1_rail_limits_2026-10-20 (h1_run.py,
h1_controls.py, h1_near_control.py, h1_floor.py); h1_cast.py is that folder's caster, copied
byte for byte (SHA-256 ebe88a40...deae44). Each sequence runs twice on a fresh default
Detector: plain, and traced with a sys.setprofile hook that records the actual returns of
estimate_rails (selected pair), _collision_core and _advisory_reason. The two runs must be
equal in every FrameResult field except timing_ms, and in the full tracker state.

usage: matrix.py OUT.json [--compare-archive DIR]   (DIR = unpacked raw-evidence.tar.xz)
"""
import dataclasses as dc
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from h1_cast import cast  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import Frame  # noqa: E402

ROOT = Path(os.environ["RESENSE_REPO"])
W = dict(walls=2.43)
HELD = dict(host=False, shadow=True, walls=2.43, shadow_distance=7.0, shadow_top=0.8)


def cases():
    out = []
    for lateral in (.68, -.68, 1.5):
        out.append(("correct_" + str(lateral), [(14, dict(lateral=lateral, host_height=.2))]))
    out.append(("correct_standard", [(14, dict(walls=2.43))]))
    for offset, lateral, distance in ((.4, 1.29, 67.), (.6, 1.5, 67.), (.4, -.68, 67.), (.6, -.68, 67.),
                                      (-.6, -1.5, 67.), (-.6, .68, 67.), (.6, 1.5, 37.), (.6, 1.5, 17.),
                                      (.6, -.68, 17.)):
        spec = dict(host_height=.2, distractor_height=.3, distractor=offset, lateral=lateral, distance=distance)
        out.append(("wrong_%s_%s_%s" % (offset, lateral, distance), [(14, spec)]))
    for distance, bed in ((67., -2.18), (17., -2.18), (67., -1.83)):
        out.append(("no_rails_%s_%s" % (distance, bed), [(14, dict(host=False, distance=distance, bed=bed, walls=2.43))]))
    out += [("loss_target_remains", [(14, W), (14, dict(host=False, walls=2.43))]),
            ("loss_target_absent", [(14, W), (14, dict(host=False, target=False, walls=2.43))]),
            ("loss_shadow_held", [(14, W), (14, dict(host=False, shadow=True, walls=2.43))]),
            ("shadow_removed_control", [(14, W), (7, dict(host=False, shadow=True, walls=2.43)), (7, W)])]
    for distance, lateral in ((17., .68), (17., -.68), (37., .68), (67., 1.29), (67., -1.5)):
        out.append(("paired_correct_%s_%s" % (distance, lateral),
                    [(14, dict(distance=distance, lateral=lateral, host_height=.2))]))
    out.append(("paired_standard_near", [(14, dict(distance=17., walls=2.43))]))
    for distance in (17., 67.):
        out.append(("wrong_inside_control_" + str(distance),
                    [(14, dict(distance=distance, host_height=.2, distractor=.6, distractor_height=.3))]))
    out.append(("actual_floor_held", [(14, W), (14, HELD)]))
    out.append(("actual_floor_recovery", [(14, W), (7, HELD), (7, W)]))
    out.append(("paired_host_near_center", [(14, dict(distance=17., lateral=0., host_height=.2))]))
    return out


def digest(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def fingerprint(x):
    """Exact canonical record (as h1_run.py): ndarray dtype/shape/bytes, IEEE float bits."""
    if dc.is_dataclass(x):
        return {f.name: fingerprint(getattr(x, f.name)) for f in dc.fields(x)}
    if isinstance(x, np.ndarray):
        return dict(dtype=x.dtype.str, shape=list(x.shape), sha256=digest(x))
    if isinstance(x, np.generic):
        return fingerprint(np.asarray(x))
    if isinstance(x, float):
        return {"f64": struct.pack(">d", x).hex()}
    if isinstance(x, dict):
        return {str(k): fingerprint(v) for k, v in sorted(x.items())}
    if isinstance(x, (list, tuple)):
        return [fingerprint(v) for v in x]
    return x


def exact_result(r, det):
    data = {f.name: fingerprint(getattr(r, f.name)) for f in dc.fields(r) if f.name != "timing_ms"}
    data["tracker"] = fingerprint(det.tracker.tracks)
    return data


def jhash(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Capture:
    """Profile hook: actual returns of the selection, core and advisory functions."""

    def __init__(self, distance):
        self.distance, self.events = distance, []

    def __call__(self, fr, event, value):
        if event != "return":
            return
        name = fr.f_code.co_name
        if name == "estimate_rails":
            self.events.append(dict(f=name, caller=fr.f_back.f_code.co_name,
                                    score=float(value.score), center=float(value.center),
                                    slabs=int(value.n_slabs)))
        elif name in ("_collision_core", "_advisory_reason"):
            b = fr.f_locals.get("b")
            if b is None or abs(float(b.pts[:, 0].mean()) - self.distance) > 1:
                return
            self.events.append(dict(f=name, line=fr.f_lineno, result=value if value is None
                                    or isinstance(value, str) else bool(value)))


def pair_class(events, spec, cfg):
    """Which physical pair the track's own estimate_rails call selected (truth = fixture geometry)."""
    fits = [e for e in events if e["f"] == "estimate_rails" and e["caller"] == "estimate_track"]
    if not fits:
        return "not_called"
    e = fits[-1]
    if e["score"] < cfg.track.rails_min_score:
        return "absent_or_insufficient"
    pairs = {"host": 0.0} if spec.get("host", True) else {}
    if spec.get("distractor") is not None:
        pairs["distractor"] = float(spec["distractor"])
    if not pairs:
        return "phantom"
    name, c = min(pairs.items(), key=lambda kv: abs(kv[1] - e["center"]))
    return name if abs(c - e["center"]) < .15 else "other(%.3f)" % e["center"]


def near(objs, spec, attr):
    d0, l0 = spec.get("distance", 67.), spec.get("lateral", .68)
    return [i for i, o in enumerate(objs) if abs(o.distance - d0) < 1 and abs(float(attr(o)) - l0) < .5]


def run_case(name, stages):
    frames = []
    for n, spec in stages:
        xyz, ring, lab = cast(**spec)
        frames += [(spec, xyz, ring, lab)] * n
    arms = []
    for traced in (False, True):
        det = Detector(DetectorConfig())
        rows = []
        for i, (spec, xyz, ring, lab) in enumerate(frames):
            if det._previous_latency_ms is not None:
                det._previous_latency_ms = 42.
            cap = Capture(spec.get("distance", 67.))
            if traced:
                sys.setprofile(cap)
            try:
                r = det.process(Frame(xyz=xyz, intensity=np.full(len(xyz), 35, np.float32), ring=ring, stamp=i * .1))
            finally:
                sys.setprofile(None)
            ex = exact_result(r, det)
            row = dict(i=i, exact=jhash(ex), fields={k: jhash(v) for k, v in ex.items()},
                       target_stop=bool(near(r.detections, spec, lambda o: o.center[1])),
                       target_warning=bool(near(r.warnings, spec, lambda o: o.center[1])),
                       target_core=any(r.candidates[j].collision_core
                                       for j in near(r.candidates, spec, lambda o: o.centroid[1])),
                       any_core=any(c.collision_core for c in r.candidates),
                       global_stop=bool(r.detections), center=float(r.track.center),
                       rail_slabs=int(r.track.rail_slabs), floor_held=bool(r.track.floor_held))
            if traced:
                row["pair"] = pair_class(cap.events, spec, det.cfg)
                row["core_returns"] = [e["result"] for e in cap.events if e["f"] == "_collision_core"]
                row["advisory"] = [e["result"] for e in cap.events if e["f"] == "_advisory_reason"]
            rows.append(row)
        arms.append(rows)
    equal = [a["exact"] == b["exact"] for a, b in zip(*arms)]
    rows = arms[1]
    for r, e in zip(rows, equal):
        r["plain_equals_traced"] = e
    return dict(name=name, stages=[dict(count=n, geometry=s) for n, s in stages], rows=rows,
                summary=dict(scans=len(rows), plain_traced_equal=sum(equal),
                             target_STOP=[r["i"] for r in rows if r["target_stop"]],
                             target_core=[r["i"] for r in rows if r["target_core"]],
                             global_STOP=[r["i"] for r in rows if r["global_stop"]],
                             pairs={p: sum(r["pair"] == p for r in rows) for p in sorted({r["pair"] for r in rows})}))


def archive_compare(report, adir):
    """Per-scan exact equality with the f56 captures (their 'exact' fingerprints, same canonical form)."""
    out = {}
    for c in report["cases"]:
        p = Path(adir) / (c["name"] + ".json")
        if not p.exists():
            out[c["name"]] = "missing"
            continue
        old = json.loads(p.read_text())["frames"]
        diff = {}
        for f, r in zip(old, c["rows"]):
            for k, v in f["exact"].items():
                if r["fields"].get(k) != jhash(v):
                    diff.setdefault(k, []).append(r["i"])
        old_stop = [f["i"] for f in old if f["target_detection_indices"]]
        old_core = [f["i"] for f in old if any(f["output"]["candidates"][j]["collision_core"]
                                               for j in f["target_candidates"])]
        out[c["name"]] = dict(field_diff_scans=diff, target_STOP_equal=old_stop == c["summary"]["target_STOP"],
                              target_core_equal=old_core == c["summary"]["target_core"])
    return out


def main():
    out = Path(sys.argv[1])
    assert not out.exists(), out
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain", "--", "resense", "configs",
                                     "native"], text=True)
    import resense
    report = dict(repo=str(ROOT), head=head, detector_tree_dirty=bool(dirty.strip()),
                  resense_file=resense.__file__, native=__import__("resense._native", fromlist=["x"]).enabled(),
                  env={k: os.environ.get(k) for k in ("OPENBLAS_CORETYPE", "OMP_NUM_THREADS")},
                  cases=[])
    for name, stages in cases():
        c = run_case(name, stages)
        report["cases"].append(c)
        s = c["summary"]
        print(name, "eq", s["plain_traced_equal"], "/", s["scans"], "STOP", s["target_STOP"], "core",
              s["target_core"], s["pairs"], flush=True)
    if "--compare-archive" in sys.argv:
        report["archive_diff_scans"] = archive_compare(report, sys.argv[sys.argv.index("--compare-archive") + 1])
    report["totals"] = dict(sequences=len(report["cases"]), scans=sum(c["summary"]["scans"] for c in report["cases"]),
                            plain_traced_equal=sum(c["summary"]["plain_traced_equal"] for c in report["cases"]))
    out.write_text(json.dumps(report, separators=(",", ":")) + "\n")
    print("TOTALS", report["totals"])
    if "archive_diff_scans" in report:
        agg = {}
        for name, d in report["archive_diff_scans"].items():
            agg["target_STOP_unequal"] = agg.get("target_STOP_unequal", 0) + (not d["target_STOP_equal"])
            agg["target_core_unequal"] = agg.get("target_core_unequal", 0) + (not d["target_core_equal"])
            for k, v in d["field_diff_scans"].items():
                agg[k] = agg.get(k, 0) + len(v)
        print("ARCHIVE_DIFF_FIELD_SCANS", agg)


if __name__ == "__main__":
    main()
