#!/usr/bin/env python3
"""Regression gate: one command, one JSON (CAPTAIN §6). Every detector / config change has to pass it.

    python scripts/regression_gate.py --out out/gate/current.json                         # measure only
    python scripts/regression_gate.py --baseline docs/evidence/results/regression_baseline_2026-09-25_ride.json
    python scripts/regression_gate.py --set cluster.min_points=8 --baseline <FILE>     # a variant
    python scripts/regression_gate.py --from-json out/gate/current.json --baseline <FILE>   # compare only
    python scripts/regression_gate.py ... --allow 'recordings.doubleT_platform.*'      # an intended trade-off

What it runs (every frame, a fresh detector per recording, the ``scripts/eval_real.py`` machinery;
the per-frame JSONL results go to ``--work``):

* the six organizer recordings (sets E and R; all six are required);
* ``cloud_with_fake_obj``, the organizers' synthetic objects (set O; required), graded per object
  with ``scripts/score_fake_objects.py``;
* the 20-minute ride ``new_data`` (set E ride, in ``--chunks`` pieces as eval_real) and the set F
  straight-track approaches (``scripts/far_range_eval.py``, the parameters of set F round 3) only
  when ``<cache>/new_data`` exists; otherwise both are reported "not available".

The JSON (``--out``) holds per recording: frames, alarm frames, alarm events (distinct confirmed
track ids), STOP episodes (GO -> STOP transitions), advisory frames, first alarm frame, alarm
distance range and, for ``doubleT_obstacle``, the labelled hits per label; per organizer object:
STOP frames, advisory-only frames, first STOP distance and frame, the distance the STOP is held from,
false STOP frames on the outside objects, background alarms; latency mean / p95 / max per
recording (informational: runs are parallel on a shared machine, never gated); the code commit,
the config hash, the native / numpy path, the date.

``--baseline FILE`` compares against an earlier JSON, prints one row per metric (better / same /
worse) and exits 1 when any **gated** metric is worse and not covered by ``--allow`` (fnmatch
patterns of metric names). Gated, i.e. "identical or better" required:

* ``frames`` of every recording and set: equal (else the data differ and nothing is comparable);
* each of the five obstacle-free recordings, and the ride: alarm events and STOP episodes must not
  rise;
* ``doubleT_obstacle``: labelled hits per label (person crossing, object on the rail, and the
  object from frame 75, after the person has left it) must not drop; the first alarm frame must not
  get later; false-alarm events (alarm tracks never matched to a label) must not rise;
* set O, every inside object: STOP frames must not drop and the first STOP must not come at a
  shorter distance (no STOP counts as the worst); every outside object: false STOP frames must not
  rise; background alarm frames and background track ids must not rise;
* set F straight (when both runs have it), per kind: sequences detected must not drop, the median
  first-confirmation distance must not shrink, false detections must not rise.

Everything else (alarm frames, advisory frames, totals, held-from distances, latency) is printed
as information. A set that only one of the two runs has is listed as "not compared". Exit codes:
0 pass, 1 a gated metric is worse, 2 usage, a missing required recording, or a set F run that
failed although the ride is cached.
"""
from __future__ import annotations

import os

if __name__ == "__main__":        # one BLAS / OpenMP thread per worker: set before numpy loads
    for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import datetime  # noqa: E402
import fnmatch  # noqa: E402
import glob  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402
import yaml  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import eval_real  # noqa: E402  (scripts/)
from score_fake_objects import score as score_set_o  # noqa: E402  (scripts/)

SCHEMA = "resense-regression-gate-v1"
SIX = list(eval_real.SIX)
LABELLED = "doubleT_obstacle"
FIVE_EMPTY = [b for b in SIX if b != LABELLED]
SET_O = "cloud_with_fake_obj"
SET_O_LABELS = "labels/cloud_with_fake_obj.json"
RIDE = "new_data"
OBJECT_ALONE_FROM = 75           # doubleT_obstacle: the person has left the object on the rail (EXPERIMENTS §0)
# set F straight track, round 3 (EXPERIMENTS §2d; experiments_2026-09-24_remeasure.json "setF.straight")
SET_F_STRAIGHT = {"files": "46,68,98,140,168,172", "kinds": "person,box1.0,box0.5,trolley,cable",
                  "start": "220", "frames": "110", "lateral": "-0.6:0.6", "seed": "0",
                  "placement-mode": "legacy", "place": "bed", "speeds": "docs/extended_dataset_intake.json"}


# --------------------------------------------------------------------------------------------
# measurement
# --------------------------------------------------------------------------------------------
def _git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def code_info() -> dict:
    """The commit and whether the detector-relevant paths differ from it."""
    import resense
    dirty = _git("status", "--porcelain", "--", "resense", "configs", "native", "setup.py")
    return {"commit": _git("rev-parse", "HEAD"), "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "version": getattr(resense, "__version__", None),
            "uncommitted_detector_changes": dirty.splitlines() if dirty else []}


def config_info(path, sets, cfg) -> dict:
    """The effective parameters and their hash (of every resolved value, so two files that resolve
    to the same detector hash the same)."""
    canon = json.dumps(cfg.to_dict(), sort_keys=True, separators=(",", ":"))
    file_sha = None
    if path and os.path.exists(path):
        with open(path, "rb") as fh:
            file_sha = hashlib.sha256(fh.read()).hexdigest()
    shown = path
    if path and os.path.abspath(path).startswith(ROOT + os.sep):
        shown = os.path.relpath(os.path.abspath(path), ROOT)
    return {"path": shown, "set": list(sets), "sha256": hashlib.sha256(canon.encode()).hexdigest(),
            "file_sha256": file_sha}


def native_info() -> dict:
    from resense import _native
    return {"path": "native" if _native.enabled() else "numpy", "status": _native.status()}


def _read_jsonl(paths):
    """[(piece index, result dict)] in processing order."""
    out = []
    for pi, p in enumerate(paths):
        with open(p, encoding="utf-8") as fh:
            out.extend((pi, json.loads(line)) for line in fh if line.strip())
    return out


def stop_stats(rows) -> dict:
    """STOP episodes (GO -> STOP transitions, counted within each piece) and the first alarm frame."""
    episodes, prev, first = 0, {}, None
    for pi, d in rows:
        if d["obstacle"] and not prev.get(pi, False):
            episodes += 1
        prev[pi] = bool(d["obstacle"])
        if d["obstacle"] and first is None:
            first = int(d["frame"])
    return {"stop_episodes": episodes, "first_alarm_frame": first}


def labelled_hits(rows, labels_path) -> dict:
    """Per label: [frames matched by an alarm, frames with the label inside the envelope and
    visible], with the one-to-one matching of ``resense.metrics.Evaluation`` (the rule of the
    185 / 246 of EXPERIMENTS); plus the object on the rail from ``OBJECT_ALONE_FROM``."""
    from resense.metrics import _assign_detections, gt_objects, load_gt
    gt = load_gt(labels_path)
    per = {}
    alone = [0, 0]
    for _, d in rows:
        frame = int(d["frame"])
        gts = [g for g in gt_objects(gt.get(f"{frame:05d}", [])) if g.in_gauge]
        assigned = _assign_detections(d["detections"], gts)
        for gi, g in enumerate(gts):
            h = per.setdefault(g.label, [0, 0])
            h[0] += int(gi in assigned)
            h[1] += 1
            if g.label == "object_on_rail" and frame >= OBJECT_ALONE_FROM:
                alone[0] += int(gi in assigned)
                alone[1] += 1
    out = {k: {"hits": v[0], "frames": v[1]} for k, v in sorted(per.items())}
    if alone[1]:
        out[f"object_on_rail_from_frame_{OBJECT_ALONE_FROM}"] = {"hits": alone[0], "frames": alone[1]}
    return out


def latency_stats(lat) -> dict:
    a = np.asarray(lat, dtype=float)
    if not a.size:
        return {"mean_ms": None, "p95_ms": None, "max_ms": None}
    return {"mean_ms": round(float(a.mean()), 1), "p95_ms": round(float(np.percentile(a, 95)), 1),
            "max_ms": round(float(a.max()), 1)}


def recording_entry(name, paths, cfg, labels_path=None) -> dict:
    """eval_real's summary of one recording plus STOP episodes, first alarm frame, labelled hits."""
    s = eval_real.summarize(name, paths, labels_path, confirm_hits=cfg.tracking.frames_to_confirm(),
                            frame_dt=cfg.tracking.frame_dt, min_hits=cfg.tracking.confirm_hits,
                            confirm_time_s=cfg.tracking.confirm_time_s,
                            stamp_dt_range=tuple(cfg.accumulation.stamp_dt_range))
    rows = _read_jsonl(paths)
    e = {"frames": s["frames"], "alarm_frames": s["alarm_frames"], "alarm_events": s["alarm_events"]}
    e.update(stop_stats(rows))
    e.update({"advisory_frames": s["advisory_frames"], "alarm_dist": s["alarm_dist"],
              "health": s["health"], "monitored_range_median": s["monitored_range_median"]})
    if labels_path:
        lab = s["labelled"]
        e["labelled"] = {"per_label": labelled_hits(rows, labels_path),
                         "hits": sum(v[0] for v in lab["per_bin"].values()),
                         "frames": sum(v[1] for v in lab["per_bin"].values()),
                         "fp_frames": lab["fp_frames"], "fp_events": lab["fp_events"],
                         "distance_error_max_m": (None if lab["distance_error_max_abs"] is None
                                                  else round(lab["distance_error_max_abs"], 2))}
    else:
        e["labelled"] = None
    return e


def set_o_entry(paths, labels_path) -> dict:
    """Per-object grade of the organizers' objects (``scripts/score_fake_objects.py``)."""
    from resense.metrics import gt_meta, load_gt
    results = [d for _, d in _read_jsonl(paths)]
    objs, bg = score_set_o(results, load_gt(labels_path))
    order = list(gt_meta(labels_path).get("objects", {})) or sorted(objs)
    objects = {}
    for label in order + sorted(set(objs) - set(order)):
        o = objs.get(label)
        if o is None:
            objects[label] = {"visible_frames": 0}
            continue
        e = {"in_gauge": o["in_gauge"], "visible_frames": o["visible_frames"],
             "first_visible_m": o["first_visible_m"], "frames_in_envelope": o["frames_in_envelope"],
             "stop_frames": o["alarm_frames"], "advisory_frames": o["advisory_only_frames"]}
        if o["in_gauge"]:
            e.update({"first_stop_m": o["first_alarm_m"], "first_stop_frame": o["first_alarm_frame"],
                      "held_from_m": o["alarm_held_from_m"]})
        else:
            e.update({"false_stop_frames": o["false_alarm_frames"], "false_stop_from_m": o["false_alarm_from_m"]})
        e["verdict"] = o["verdict"]
        e["bins"] = o["bins"]
        objects[label] = e
    inside = [e for e in objects.values() if e.get("in_gauge")]
    outside = [e for e in objects.values() if e.get("in_gauge") is False]
    return {"available": True, "frames": bg["frames"], "alarm_frames": bg["alarm_frames"],
            "inside_stop_frames": sum(e["stop_frames"] for e in inside),
            "inside_visible_frames": sum(e["visible_frames"] for e in inside),
            "inside_objects_with_stop": sum(1 for e in inside if e["stop_frames"]),
            "inside_objects": len(inside),
            "outside_false_stop_frames": sum(e["false_stop_frames"] for e in outside),
            "background": {"alarm_frames": bg["background_alarm_frames"], "track_ids": bg["background_alarm_ids"]},
            "objects": objects}


def run_set_f_straight(cache, cfg_path, work, jobs) -> dict:
    """Set F straight track through ``scripts/far_range_eval.py`` with the effective config."""
    out = os.path.join(work, "setF_straight.json")
    cmd = [sys.executable, os.path.join(HERE, "far_range_eval.py"), "--cache", os.path.join(cache, RIDE),
           "--config", cfg_path, "--jobs", str(jobs), "--out", out]
    cmd += [f"--{k}={v}" for k, v in SET_F_STRAIGHT.items()]      # "=": "--lateral -0.6:0.6" reads as an option
    env = dict(os.environ, PYTHONPATH=ROOT + os.pathsep + os.environ.get("PYTHONPATH", ""))
    r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    if r.returncode != 0:            # the ride is cached, so this is a broken run, not missing data
        return {"available": False, "error": True,
                "reason": f"far_range_eval.py failed: {r.stderr.strip()[-400:]}"}
    with open(out, encoding="utf-8") as fh:
        rep = json.load(fh)
    kinds = {}
    for kind, s in rep["summary"]["per_kind"].items():
        kinds[kind] = {"sequences": s["sequences"], "detected": s["detected"],
                       "first_detection_median_m": s["first_detection_median"],
                       "sustained_median_m": s["sustained_median"], "false_detections": s["false_detections"],
                       "recall_by_bin": s["recall_by_bin"]}
    return {"available": True, "parameters": dict(SET_F_STRAIGHT), "kinds": kinds}


def measure(a) -> dict:
    """Run everything and return the result dict (the JSON of the gate)."""
    from resense.io import _natural_key, load_cache_stamps
    os.makedirs(a.work, exist_ok=True)
    cfg_dict = eval_real.load_cfg_dict(a.config, a.set)
    cfg = eval_real.load_cfg(a.config, a.set)          # fail fast on an unknown key
    cfg_path = os.path.join(os.path.abspath(a.work), "config.yaml")
    with open(cfg_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump({"resense": cfg_dict}, fh, sort_keys=False)
    ride_dir = os.path.join(a.cache, RIDE)
    have_ride = bool(glob.glob(os.path.join(ride_dir, "*.npy")))
    names = SIX + [SET_O] + ([RIDE] if have_ride else [])
    jobs, pieces = [], {}
    for name in names:
        d = os.path.join(a.cache, name)
        files = sorted(glob.glob(os.path.join(d, "*.npy")), key=_natural_key)
        if not files:
            print(f"regression_gate: no cached frames in {d} (the six recordings and {SET_O} are required)",
                  file=sys.stderr)
            raise SystemExit(2)
        stamps = load_cache_stamps(d)
        if a.nominal_stamps:
            stamps = eval_real.nominal_stamps(stamps)
        n = a.chunks if name == RIDE else 1
        for k, part in enumerate(np.array_split(np.array(files), n)):
            out = os.path.join(a.work, f"{name}.jsonl" if n == 1 else f"{name}_{k}.jsonl")
            jobs.append((name, list(part), cfg_dict, out, stamps, None))
            pieces.setdefault(name, []).append(out)
    jobs.sort(key=lambda j: -len(j[1]))                   # longest first
    t0 = time.time()
    lat = {}
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for name, _path, lats in ex.map(eval_real.run_piece, jobs):
            lat.setdefault(name, []).extend(lats)
    recordings = {b: recording_entry(b, pieces[b], cfg,
                                     os.path.join(ROOT, eval_real.LABELS[b]) if b in eval_real.LABELS else None)
                  for b in SIX}
    five = {k: sum(recordings[b][k] for b in FIVE_EMPTY)
            for k in ("frames", "alarm_frames", "alarm_events", "stop_episodes", "advisory_frames")}
    set_o = set_o_entry(pieces[SET_O], os.path.join(ROOT, SET_O_LABELS))
    if have_ride:
        r = recording_entry(RIDE, pieces[RIDE], cfg)
        # the frame index of a ride piece is its position in the piece: no meaningful first alarm frame
        ride = {"available": True, "chunks": a.chunks,
                **{k: v for k, v in r.items() if k not in ("labelled", "first_alarm_frame")}}
        set_f = run_set_f_straight(a.cache, cfg_path, a.work, a.jobs)
    else:
        why = f"no cache in {ride_dir}"
        ride = {"available": False, "reason": why}
        set_f = {"available": False, "reason": why}
    return {
        "schema": SCHEMA,
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "code": code_info(),
        "config": config_info(a.config, a.set, cfg),
        "native": native_info(),
        "run": {"cache": os.path.abspath(a.cache), "jobs": a.jobs, "nominal_stamps": a.nominal_stamps,
                "wall_s": round(time.time() - t0, 1),
                "machine": {"cpus": os.cpu_count(), "platform": platform.platform(),
                            "python": platform.python_version(), "numpy": np.__version__}},
        "recordings": recordings,
        "five_empty": five,
        "ride": ride,
        "set_O": set_o,
        "set_F_straight": set_f,
        "latency_ms": {"note": "timing_ms.total per frame; informational, never gated: the workers run in "
                               "parallel on a shared machine (clean timing: EXPERIMENTS §3)",
                       **{k: latency_stats(lat[k]) for k in names if k in lat}},
    }


# --------------------------------------------------------------------------------------------
# comparison
# --------------------------------------------------------------------------------------------
HIGHER, LOWER, EQUAL, INFO = "higher", "lower", "equal", "info"


def metrics(result: dict) -> dict:
    """{metric name: (value, direction, gated)} of a gate JSON; the names are what --allow matches."""
    m = {}

    def put(key, value, direction, gated):
        m[key] = (value, direction, gated)

    for bag, r in (result.get("recordings") or {}).items():
        k = f"recordings.{bag}"
        empty = bag in FIVE_EMPTY
        put(f"{k}.frames", r.get("frames"), EQUAL, True)
        put(f"{k}.alarm_events", r.get("alarm_events"), LOWER, empty)
        put(f"{k}.stop_episodes", r.get("stop_episodes"), LOWER, empty)
        put(f"{k}.alarm_frames", r.get("alarm_frames"), LOWER, False)
        put(f"{k}.advisory_frames", r.get("advisory_frames"), LOWER, False)
        lab = r.get("labelled")
        if lab:
            put(f"{k}.first_alarm_frame", r.get("first_alarm_frame"), LOWER, True)
            for label, h in (lab.get("per_label") or {}).items():
                put(f"{k}.labelled.{label}.hits", h.get("hits"), HIGHER, True)
            put(f"{k}.labelled.hits", lab.get("hits"), HIGHER, False)
            put(f"{k}.labelled.fp_events", lab.get("fp_events"), LOWER, True)
            put(f"{k}.labelled.distance_error_max_m", lab.get("distance_error_max_m"), LOWER, False)
    for key in ("alarm_events", "stop_episodes", "alarm_frames"):
        if key in (result.get("five_empty") or {}):
            put(f"five_empty.{key}", result["five_empty"][key], LOWER, False)
    ride = result.get("ride") or {}
    if ride.get("available"):
        put("ride.frames", ride.get("frames"), EQUAL, True)
        put("ride.alarm_events", ride.get("alarm_events"), LOWER, True)
        put("ride.stop_episodes", ride.get("stop_episodes"), LOWER, True)
        put("ride.alarm_frames", ride.get("alarm_frames"), LOWER, False)
    so = result.get("set_O") or {}
    if so.get("available"):
        put("set_O.frames", so.get("frames"), EQUAL, True)
        for label, o in (so.get("objects") or {}).items():
            k = f"set_O.objects.{label}"
            if o.get("in_gauge"):
                put(f"{k}.stop_frames", o.get("stop_frames"), HIGHER, True)
                put(f"{k}.first_stop_m", o.get("first_stop_m"), HIGHER, True)
                put(f"{k}.held_from_m", o.get("held_from_m"), HIGHER, False)
                put(f"{k}.advisory_frames", o.get("advisory_frames"), INFO, False)
            elif o.get("in_gauge") is False:
                put(f"{k}.false_stop_frames", o.get("false_stop_frames"), LOWER, True)
                put(f"{k}.advisory_frames", o.get("advisory_frames"), INFO, False)
        bg = so.get("background") or {}
        put("set_O.background.alarm_frames", bg.get("alarm_frames"), LOWER, True)
        put("set_O.background.track_ids", bg.get("track_ids"), LOWER, True)
        put("set_O.inside_stop_frames", so.get("inside_stop_frames"), HIGHER, False)
        put("set_O.outside_false_stop_frames", so.get("outside_false_stop_frames"), LOWER, False)
    sf = result.get("set_F_straight") or {}
    if sf.get("available"):
        for kind, s in (sf.get("kinds") or {}).items():
            k = f"set_F_straight.{kind}"
            put(f"{k}.detected", s.get("detected"), HIGHER, True)
            put(f"{k}.first_detection_median_m", s.get("first_detection_median_m"), HIGHER, True)
            put(f"{k}.false_detections", s.get("false_detections"), LOWER, True)
            put(f"{k}.sustained_median_m", s.get("sustained_median_m"), HIGHER, False)
    for name, s in (result.get("latency_ms") or {}).items():
        if isinstance(s, dict):
            put(f"latency_ms.{name}.mean", s.get("mean_ms"), LOWER, False)
            put(f"latency_ms.{name}.p95", s.get("p95_ms"), LOWER, False)
    return m


def verdict(base, new, direction) -> str:
    """better / same / worse / differs / changed. ``None`` is the worst value: never alarmed,
    never detected (a missing first STOP, first alarm frame or first-detection distance)."""
    if base == new:
        return "same"
    if direction == EQUAL:
        return "differs"
    if direction == INFO:
        return "changed"
    if base is None or new is None:
        return "better" if base is None else "worse"
    if direction == HIGHER:
        return "better" if new > base else "worse"
    return "better" if new < base else "worse"


def compare(base: dict, new: dict, allow=()) -> list:
    """One row per metric of either run: metric, baseline, current, verdict, gated, allowed, fails."""
    mb, mn = metrics(base), metrics(new)
    rows = []
    for key in list(mb) + [k for k in mn if k not in mb]:
        if key not in mb or key not in mn:
            vb = mb[key][0] if key in mb else None
            vn = mn[key][0] if key in mn else None
            rows.append({"metric": key, "baseline": vb, "current": vn,
                         "verdict": "not in baseline" if key not in mb else "not in this run",
                         "gated": False, "allowed": False, "fails": False})
            continue
        vb, direction, gated_b = mb[key]
        vn, _, gated_n = mn[key]
        gated = gated_b or gated_n
        v = verdict(vb, vn, direction)
        allowed = any(fnmatch.fnmatchcase(key, p) for p in allow)
        bad = gated and v in ("worse", "differs")
        rows.append({"metric": key, "baseline": vb, "current": vn, "verdict": v, "gated": gated,
                     "allowed": bad and allowed, "fails": bad and not allowed})
    return rows


def unavailable(base: dict, new: dict) -> list:
    """Optional sets present in one run and not in the other (not compared; said so), and run
    settings that make the two runs unlike (the ride's pieces, the stamps)."""
    out = []
    for key, label in (("ride", "ride (set E)"), ("set_F_straight", "set F straight")):
        b = bool((base.get(key) or {}).get("available"))
        n = bool((new.get(key) or {}).get("available"))
        if b != n:
            out.append(f"{label}: {'baseline only' if b else 'this run only'}; not compared")
        elif not b:
            reason = (new.get(key) or {}).get("reason") or (base.get(key) or {}).get("reason") or ""
            out.append(f"{label}: not available in either run ({reason})")
    rb, rn = base.get("run") or {}, new.get("run") or {}
    if bool(rb.get("nominal_stamps")) != bool(rn.get("nominal_stamps")):
        out.append(f"stamps differ (nominal_stamps {rb.get('nominal_stamps')} -> {rn.get('nominal_stamps')}): "
                   "not like for like")
    cb, cn = (base.get("ride") or {}).get("chunks"), (new.get("ride") or {}).get("chunks")
    if cb and cn and cb != cn:
        out.append(f"ride pieces differ ({cb} -> {cn}): events split at piece boundaries differ")
    return out


def _fmt(v) -> str:
    if v is None:
        return "-"
    return str(v)


def table(rows, changed_only=False) -> str:
    """The comparison as text: ``gate`` marks the gated rows, ``<< FAIL`` a gated row that got worse."""
    w = max([len("metric")] + [len(r["metric"]) for r in rows])
    lines = [f"{'metric':{w}s} {'gate':>4s} {'baseline':>10s} {'current':>10s}  verdict"]
    for r in rows:
        if changed_only and r["verdict"] == "same":
            continue
        mark = "  << FAIL" if r["fails"] else "  (allowed by --allow)" if r["allowed"] else ""
        lines.append(f"{r['metric']:{w}s} {'yes' if r['gated'] else '':>4s} {_fmt(r['baseline']):>10s} "
                     f"{_fmt(r['current']):>10s}  {r['verdict']}{mark}")
    return "\n".join(lines)


def gate_summary(rows, base: dict, baseline_path: str, allow) -> dict:
    fails = [r["metric"] for r in rows if r["fails"]]
    return {"baseline": baseline_path,
            "baseline_commit": (base.get("code") or {}).get("commit"),
            "baseline_config_sha256": (base.get("config") or {}).get("sha256"),
            "allow": list(allow), "passed": not fails, "worse_gated": fails,
            "worse_allowed": [r["metric"] for r in rows if r["allowed"]],
            "better": [r["metric"] for r in rows if r["gated"] and r["verdict"] == "better"],
            "same": sum(1 for r in rows if r["verdict"] == "same"),
            "info_changed": [r["metric"] for r in rows if not r["gated"]
                             and r["verdict"] not in ("same", "not in baseline", "not in this run")]}


# --------------------------------------------------------------------------------------------
def print_result(res: dict) -> None:
    rec = res["recordings"]
    print(f"code {res['code'].get('commit')}  config {res['config']['sha256'][:12]} {res['config']['set'] or ''}  "
          f"{res['native']['status']}")
    print(f"{'recording':38s} {'frames':>6s} {'alarmF':>6s} {'events':>6s} {'STOPep':>6s} {'advis':>6s} {'1st':>4s}")
    for b, r in rec.items():
        print(f"{b:38s} {r['frames']:6d} {r['alarm_frames']:6d} {r['alarm_events']:6d} {r['stop_episodes']:6d} "
              f"{r['advisory_frames']:6d} {_fmt(r['first_alarm_frame']):>4s}")
        if r.get("labelled"):
            lab = r["labelled"]
            per = ", ".join(f"{k} {v['hits']}/{v['frames']}" for k, v in lab["per_label"].items())
            print(f"   labelled {lab['hits']}/{lab['frames']}: {per}; fp events {lab['fp_events']}, "
                  f"distance error <= {lab['distance_error_max_m']} m")
    f = res["five_empty"]
    print(f"five obstacle-free recordings: {f['alarm_frames']} alarm frames / {f['alarm_events']} events / "
          f"{f['stop_episodes']} STOP episodes in {f['frames']} frames")
    ride = res["ride"]
    print("ride (set E): " + (f"{ride['alarm_frames']} / {ride['alarm_events']} / {ride['stop_episodes']} in "
                              f"{ride['frames']} frames" if ride.get("available") else f"not available ({ride['reason']})"))
    so = res["set_O"]
    print(f"set O: STOP in {so['inside_stop_frames']} of {so['inside_visible_frames']} visible inside object-frames "
          f"({so['inside_objects_with_stop']} of {so['inside_objects']} objects), {so['outside_false_stop_frames']} "
          f"false STOP frames outside, background {so['background']['alarm_frames']} frames / "
          f"{so['background']['track_ids']} ids")
    for label, o in so["objects"].items():
        if o.get("in_gauge"):
            print(f"   {label:20s} inside   STOP {o['stop_frames']:3d}/{o['visible_frames']:3d} advisory "
                  f"{o['advisory_frames']:3d} first STOP {_fmt(o['first_stop_m'])} m held from {_fmt(o['held_from_m'])} m")
        elif o.get("in_gauge") is False:
            print(f"   {label:20s} outside  false STOP {o['false_stop_frames']:3d}/{o['visible_frames']:3d} "
                  f"advisory {o['advisory_frames']:3d}")
    sf = res["set_F_straight"]
    if sf.get("available"):
        for kind, s in sf["kinds"].items():
            print(f"set F straight {kind:8s} detected {s['detected']}/{s['sequences']}, first median "
                  f"{_fmt(s['first_detection_median_m'])} m, false {s['false_detections']}")
    else:
        print(f"set F straight: not available ({sf['reason']})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--config", default=os.path.join(ROOT, "configs", "default.yaml"))
    ap.add_argument("--set", action="append", default=[], help="section.key=value override (YAML value)")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--chunks", type=int, default=8, help="pieces of the ride (as scripts/eval_real.py)")
    ap.add_argument("--nominal-stamps", action="store_true",
                    help="snap the cached receive stamps to the 10 Hz rotation (eval_real --nominal-stamps)")
    ap.add_argument("--work", default="out/regression_gate", help="per-frame JSONL results and the effective config")
    ap.add_argument("--out", default=None, help="write the JSON here (default <work>/result.json)")
    ap.add_argument("--from-json", default=None, metavar="FILE", help="do not run: compare this earlier result")
    ap.add_argument("--baseline", default=None, metavar="FILE", help="compare and gate against this JSON")
    ap.add_argument("--allow", action="append", default=[], metavar="PATTERN",
                    help="metric names (fnmatch) allowed to get worse: an intended, documented trade-off")
    ap.add_argument("--changed-only", action="store_true", help="print only the rows that changed")
    a = ap.parse_args(argv)
    if a.from_json:
        with open(a.from_json, encoding="utf-8") as fh:
            res = json.load(fh)
    else:
        res = measure(a)
    print_result(res)
    code = 0
    if a.baseline:
        with open(a.baseline, encoding="utf-8") as fh:
            base = json.load(fh)
        rows = compare(base, res, a.allow)
        print()
        print(f"baseline {a.baseline}: code {(base.get('code') or {}).get('commit')}, config "
              f"{((base.get('config') or {}).get('sha256') or '')[:12]}, {(base.get('native') or {}).get('status')}")
        print(table(rows, a.changed_only))
        for line in unavailable(base, res):
            print("note:", line)
        g = gate_summary(rows, base, a.baseline, a.allow)
        res["gate"] = g
        counts = (f"{len(g['better'])} gated better, {len(g['worse_allowed'])} worse but allowed, "
                  f"{len(g['info_changed'])} information rows changed")
        if g["passed"]:
            print(f"GATE PASS: no gated metric worse ({counts})")
        else:
            print(f"GATE FAIL: {len(g['worse_gated'])} gated metric(s) worse: {', '.join(g['worse_gated'])} ({counts})")
            code = 1
    out = a.out or (None if a.from_json else os.path.join(a.work, "result.json"))
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print(f"wrote {out}")
    if (res.get("set_F_straight") or {}).get("error"):
        print(f"ERROR: the ride is cached but set F straight did not run: {res['set_F_straight']['reason']}",
              file=sys.stderr)
        return 2
    return code


if __name__ == "__main__":
    sys.exit(main())
