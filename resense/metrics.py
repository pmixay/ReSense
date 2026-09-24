"""Evaluation: match detections against ground truth, recall vs range, false positives.

Two levels of false-alarm accounting (docs/EVALUATION.md section 2):

* **frames** — frames with ``obstacle = true`` that have no gauge ground truth (``fp_frames``);
* **events** — distinct confirmed gauge track ids (``detections[].id`` of the status JSON,
  scoped by the injected sequence when the tracker restarts)
  that were never matched to a ground-truth object (``fp_events``). One object that stays
  in the corridor for 50 frames is one event; this is the headline number, reported per
  hour of bag time (from the ``stamp`` field) and per km when a speed is known (a constant
  ``speed_mps`` passed to :meth:`Evaluation.add_frame`, or a per-frame ``ego_speed_mps`` /
  ``ego_speed`` key in the result dict).

Frame indices (the ``frame`` key that ``resense run`` writes) are used to detect the
subsampling stride: with every N-th frame, the consecutive hits a track needs
(``tracking.frames_to_confirm()``: ``confirm_hits`` / ``confirm_time_s``) are ``N * frame_dt``
seconds apart, so a candidate must persist ``confirm_hits * N * frame_dt`` seconds instead of
``confirm_hits * frame_dt`` -- subsampled false-alarm counts understate
the rate the node shows at 10 Hz. :meth:`Evaluation.summary` says so (``stride_caveat``).

Ground-truth files: ``gt.json`` as written by ``resense inject`` and by the label tool
(docs/DATASET.md "Label format"), loaded with :func:`load_gt`.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set

import numpy as np
from scipy.optimize import linear_sum_assignment

RANGE_BINS = [(0, 50), (50, 100), (100, 150), (150, 200), (200, 300)]

GT_KEY_WIDTH = 5   # frame keys in gt.json: zero-padded bag frame index, e.g. "00042"


def gt_key(frame_index: int) -> str:
    """The gt.json key of a bag frame: its zero-padded index in message order."""
    return f"{int(frame_index):0{GT_KEY_WIDTH}d}"


@dataclass
class GTObstacle:
    distance: float       # m along the track (nearest face)
    lateral: float        # m from the track axis
    size: Sequence[float] = (0.5, 0.5, 0.5)
    label: str = "obstacle"
    in_gauge: bool = True
    kind: str = ""        # object class for the per-class table ("name" of the catalogue, else "kind")

    @classmethod
    def from_dict(cls, d: dict) -> "GTObstacle":
        """Accepts the ``inject`` row keys, or a label-tool row with a ``bbox``
        ``[[xmin, ymin, zmin], [xmax, ymax, zmax]]`` (vehicle frame) instead of
        ``distance`` / ``lateral`` / ``size``."""
        bbox = d.get("bbox")
        if bbox is not None and ("distance" not in d or "size" not in d):
            lo, hi = (np.asarray(v, dtype=float) for v in bbox)
            d = dict(d)
            d.setdefault("distance", float(lo[0]))
            d.setdefault("lateral", float(0.5 * (lo[1] + hi[1])))
            d.setdefault("size", [float(v) for v in (hi - lo)])
        return cls(distance=float(d["distance"]), lateral=float(d.get("lateral", 0.0)),
                   size=tuple(d.get("size", (0.5, 0.5, 0.5))), label=str(d.get("label", "obstacle")),
                   in_gauge=bool(d.get("in_gauge", True)),
                   kind=str(d.get("name", d.get("kind", ""))))


def load_gt(path: str) -> Dict[str, list]:
    """Read a gt.json (``{"00042": [row, ...], ...}``); keys starting with ``_`` are metadata
    (``_meta``) and are dropped."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def gt_meta(path: str) -> dict:
    """The ``_meta`` block of a gt.json ({} when absent)."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    meta = raw.get("_meta", {})
    return meta if isinstance(meta, dict) else {}


def gt_row_speed(rows: Sequence[dict]) -> Optional[float]:
    """The simulated train speed (m/s) of an ``inject --sequence`` frame: the ``speed_mps``
    of its rows when it is positive, else None (static injected frames write 0.0 and real
    labels carry no speed, so the detector is given nothing for them)."""
    for r in rows:
        v = r.get("speed_mps")
        if v is not None and float(v) > 0.0:
            return float(v)
    return None


def gt_objects(rows: Sequence[dict], skip_occluded: bool = True) -> List[GTObstacle]:
    """Rows of one frame -> GTObstacle list; rows with ``n_points == 0`` (object fully
    occluded by real geometry) are dropped when ``skip_occluded`` (they count separately)."""
    return [GTObstacle.from_dict(r) for r in rows if not (skip_occluded and r.get("n_points", 1) == 0)]


def match(det_distance: float, det_lateral: float, gt: GTObstacle,
          tol_base: float = 2.0, tol_rel: float = 0.03, lateral_tol: float = 1.0) -> bool:
    tol = max(tol_base, tol_rel * gt.distance) + 0.5 * max(gt.size[0], 0.0)
    return abs(det_distance - gt.distance) <= tol and abs(det_lateral - gt.lateral) <= lateral_tol


def _assign_detections(dets: Sequence[dict], gts: Sequence[GTObstacle]) -> Dict[int, int]:
    """Match as many objects as possible, then prefer the smallest position errors.

    A first-fit loop can assign a shared detection to the wrong object and miss another
    object that had a unique compatible detection. Dummy columns represent misses.
    """
    if not dets or not gts:
        return {}
    n_det = len(dets)
    cost = np.full((len(gts), n_det + len(gts)), 10.0)
    cost[:, :n_det] = 1e6
    for gi, gt in enumerate(gts):
        distance_tol = max(2.0, 0.03 * gt.distance) + 0.5 * max(gt.size[0], 0.0)
        for di, det in enumerate(dets):
            dx = abs(float(det["distance"]) - gt.distance)
            dy = abs(float(det["lateral"]) - gt.lateral)
            if match(float(det["distance"]), float(det["lateral"]), gt):
                cost[gi, di] = dx / distance_tol + dy
    gt_idx, det_idx = linear_sum_assignment(cost)
    return {int(gi): int(di) for gi, di in zip(gt_idx, det_idx) if di < n_det and cost[gi, di] < 10.0}


def _bin_order(key: str) -> float:
    """Sort key of a range-bin label (``"50-100"``, ``"300+"``)."""
    return float(key.split("-")[0].rstrip("+"))


def frame_stride(frame_indices: Sequence[int]) -> Optional[int]:
    """Most common step between consecutive frame indices (1 = every frame), None if unknown."""
    idx = [int(i) for i in frame_indices if i is not None]
    if len(idx) < 2:
        return None
    steps = [b - a for a, b in zip(idx[:-1], idx[1:]) if b > a]
    if not steps:
        return None
    return int(Counter(steps).most_common(1)[0][0])


@dataclass
class Evaluation:
    n_frames: int = 0
    n_empty_frames: int = 0
    fp_frames: int = 0                     # empty frames with an obstacle alarm
    fp_detections: int = 0                 # unmatched gauge detections (all frames)
    tp: int = 0
    fn: int = 0
    per_bin: Dict[str, List[int]] = field(default_factory=dict)   # "lo-hi": [tp, total]
    first_detection: Dict[str, float] = field(default_factory=dict)  # gt label -> max distance detected
    latency_ms: List[float] = field(default_factory=list)
    # --- additive (Sprint 2): events, advisory frames, bag time, distance, stride ---------
    confirm_hits: int = 3                  # frames a static object needs to be confirmed (tracking.frames_to_confirm()), for the stride caveat
    frame_dt: float = 0.1                  # tracking.frame_dt (s)
    alarm_frames: int = 0                  # frames with obstacle = true (all frames)
    advisory_frames: int = 0               # frames with warning = true (all frames)
    alarm_ids: Set[tuple] = field(default_factory=set)      # (sequence, track id): ids may restart between sequences
    matched_ids: Set[tuple] = field(default_factory=set)    # ... matched to a gt object at least once
    unmatched_ids: Set[tuple] = field(default_factory=set)  # ... unmatched in at least one frame
    per_class: Dict[str, List[int]] = field(default_factory=dict)   # class: [tp, total]
    per_class_bin: Dict[str, Dict[str, List[int]]] = field(default_factory=dict)  # class: {"lo-hi": [tp, total]}
    stamps: List[float] = field(default_factory=list)
    frame_indices: List[Optional[int]] = field(default_factory=list)
    alarm_distances: List[float] = field(default_factory=list)
    distance_m: float = 0.0                # travelled distance integrated from speed x stamp gaps
    speed_known: bool = False
    scoped_time_s: float = 0.0             # duration within independent injected sequences
    has_event_scope: bool = False
    last_timed_stamp: Optional[float] = None
    last_timed_scope: object = None
    # --- additive (real labels, 21.09): errors of matched detections, accumulation bookkeeping ---
    distance_errors: List[float] = field(default_factory=list)   # det - gt distance (m) of every match
    lateral_errors: List[float] = field(default_factory=list)    # det - gt lateral (m) of every match
    ego_speed_sources: Counter = field(default_factory=Counter)  # ego_speed_source value -> frames
    n_accumulated: List[int] = field(default_factory=list)       # frames merged per result
    first_alarm_frame: Optional[int] = None                      # frame index (or position) of the first alarm

    def add_frame(self, result_dict: dict, gts: Sequence[GTObstacle], use_candidates: bool = False,
                  speed_mps: Optional[float] = None, frame_index: Optional[int] = None,
                  event_scope=None) -> None:
        """Account one frame. ``result_dict`` is ``FrameResult.to_dict()`` (plus the ``frame``
        key that ``resense run`` adds); ``gts`` the ground truth of that frame (empty = no
        object). ``speed_mps`` (constant) or a per-frame ``ego_speed_mps`` / ``ego_speed`` key
        turns bag time into travelled distance."""
        self.n_frames += 1
        dets = result_dict["detections"]
        if use_candidates:
            dets = dets + result_dict.get("warnings", [])
        self.latency_ms.append(result_dict.get("timing_ms", {}).get("total", 0.0))
        used = np.zeros(len(dets), dtype=bool)
        gauge_gts = [g for g in gts if g.in_gauge]
        assignments = _assign_detections(dets, gauge_gts)
        if event_scope is None:
            event_scope = result_dict.get("event_scope", result_dict.get("seq"))
        if not gauge_gts:
            self.n_empty_frames += 1
            if result_dict["obstacle"]:
                self.fp_frames += 1
        for gi, g in enumerate(gauge_gts):
            key = None
            for lo, hi in RANGE_BINS:
                if lo <= g.distance < hi:
                    key = f"{lo}-{hi}"
            if key is None:
                key = f"{RANGE_BINS[-1][1]}+"
            self.per_bin.setdefault(key, [0, 0])
            self.per_bin[key][1] += 1
            cls_key = g.kind or "obstacle"
            self.per_class.setdefault(cls_key, [0, 0])
            self.per_class[cls_key][1] += 1
            self.per_class_bin.setdefault(cls_key, {}).setdefault(key, [0, 0])
            self.per_class_bin[cls_key][key][1] += 1
            if gi in assignments:
                i = assignments[gi]
                d = dets[i]
                used[i] = True
                if "id" in d:
                    self.matched_ids.add((event_scope, int(d["id"])))
                self.distance_errors.append(float(d["distance"]) - g.distance)
                self.lateral_errors.append(float(d["lateral"]) - g.lateral)
                self.tp += 1
                self.per_bin[key][0] += 1
                self.per_class[cls_key][0] += 1
                self.per_class_bin[cls_key][key][0] += 1
                self.first_detection[g.label] = max(self.first_detection.get(g.label, 0.0), g.distance)
            else:
                self.fn += 1
        self.fp_detections += int((~used).sum())
        for i, d in enumerate(dets):
            if "id" in d:
                scoped_id = (event_scope, int(d["id"]))
                self.alarm_ids.add(scoped_id)
                if not used[i]:
                    self.unmatched_ids.add(scoped_id)
        # --- frame-level bookkeeping ---
        if result_dict.get("obstacle"):
            self.alarm_frames += 1
            nd = result_dict.get("nearest_distance")
            if nd is not None:
                self.alarm_distances.append(float(nd))
        if result_dict.get("warning"):
            self.advisory_frames += 1
        stamp = result_dict.get("stamp")
        if speed_mps is None:
            speed_mps = result_dict.get("ego_speed_mps", result_dict.get("ego_speed"))
        if event_scope is not None:
            self.has_event_scope = True
        if stamp is not None:
            stamp = float(stamp)
            if self.last_timed_stamp is not None and event_scope == self.last_timed_scope:
                dt = max(stamp - self.last_timed_stamp, 0.0)
                self.scoped_time_s += dt
                if speed_mps is not None:
                    self.distance_m += float(speed_mps) * dt
            self.stamps.append(stamp)
            self.last_timed_stamp = stamp
        else:
            # A missing stamp breaks distance integration in a continuous bag as well:
            # elapsed time since the previous known stamp is no longer attributable.
            self.last_timed_stamp = None
        self.last_timed_scope = event_scope
        if speed_mps is not None:
            self.speed_known = True
        if frame_index is None:
            frame_index = result_dict.get("frame")
        self.frame_indices.append(None if frame_index is None else int(frame_index))
        if result_dict.get("obstacle") and self.first_alarm_frame is None:
            self.first_alarm_frame = int(frame_index) if frame_index is not None else self.n_frames - 1
        src = result_dict.get("ego_speed_source")
        if src is not None:
            self.ego_speed_sources[str(src)] += 1
        if result_dict.get("n_accumulated") is not None:
            self.n_accumulated.append(int(result_dict["n_accumulated"]))

    # --- derived quantities -------------------------------------------------------------
    @property
    def fp_events(self) -> int:
        """Distinct confirmed gauge track ids never matched to a ground-truth object."""
        return len(self.unmatched_ids - self.matched_ids)

    @property
    def alarm_events(self) -> int:
        """Distinct confirmed gauge track ids (all frames)."""
        return len(self.alarm_ids)

    @property
    def bag_time_s(self) -> float:
        if self.has_event_scope:
            return self.scoped_time_s
        return (max(self.stamps) - min(self.stamps)) if len(self.stamps) >= 2 else 0.0

    @property
    def stride(self) -> Optional[int]:
        return frame_stride([i for i in self.frame_indices if i is not None])

    def stride_caveat(self) -> Optional[str]:
        s = self.stride
        if s is None or s <= 1:
            return None
        return (f"frames are every {s}th bag frame: the {self.confirm_hits} consecutive "
                f"hits a track needs are {s * self.frame_dt:.1f} s apart, so a candidate must persist "
                f"{self.confirm_hits * s * self.frame_dt:.1f} s to be confirmed instead of "
                f"{self.confirm_hits * self.frame_dt:.1f} s at 10 Hz; subsampled alarm and false-alarm "
                f"counts understate the full-rate values (run every frame for the headline numbers)")

    def summary(self) -> dict:
        rec = {k: (v[0] / v[1] if v[1] else None) for k, v in sorted(self.per_bin.items(), key=lambda kv: _bin_order(kv[0]))}
        hours = self.bag_time_s / 3600.0
        km = self.distance_m / 1000.0
        lat = np.asarray(self.latency_ms, dtype=float)
        derr = np.asarray(self.distance_errors, dtype=float)
        lerr = np.asarray(self.lateral_errors, dtype=float)
        return {
            # --- keys that existed before Sprint 2 (frozen) ---
            "frames": self.n_frames, "empty_frames": self.n_empty_frames,
            "recall": (self.tp / (self.tp + self.fn)) if (self.tp + self.fn) else None,
            "recall_by_range": rec, "per_bin_counts": self.per_bin,
            "fp_frames": self.fp_frames,
            "fp_frame_rate": (self.fp_frames / self.n_empty_frames) if self.n_empty_frames else None,
            "fp_detections": self.fp_detections,
            "first_detection_distance": self.first_detection,
            "latency_ms_mean": float(lat.mean()) if lat.size else None,
            "latency_ms_p95": float(np.percentile(lat, 95)) if lat.size else None,
            # --- additive ---
            "latency_ms_max": float(lat.max()) if lat.size else None,
            "recall_by_class": {k: (v[0] / v[1] if v[1] else None) for k, v in sorted(self.per_class.items())},
            "per_class_counts": self.per_class,
            "alarm_frames": self.alarm_frames,
            "alarm_events": self.alarm_events,
            "alarm_distance_min": min(self.alarm_distances) if self.alarm_distances else None,
            "alarm_distance_max": max(self.alarm_distances) if self.alarm_distances else None,
            "advisory_frames": self.advisory_frames,
            "advisory_frame_rate": (self.advisory_frames / self.n_frames) if self.n_frames else None,
            "fp_events": self.fp_events,
            "bag_time_s": self.bag_time_s,
            "fp_events_per_hour": (self.fp_events / hours) if hours > 0 else None,
            "distance_km": km if self.speed_known else None,
            # at least 10 m travelled: the estimator's ~0 m/s on a stationary bag gives a meaningless rate
            "fp_events_per_km": (self.fp_events / km) if (self.speed_known and km >= 0.01) else None,
            "frame_stride": self.stride,
            "stride_caveat": self.stride_caveat(),
            # --- additive (21.09): matched-detection errors, first alarm, accumulation bookkeeping ---
            "distance_error_mean_abs": float(np.mean(np.abs(derr))) if derr.size else None,
            "distance_error_max_abs": float(np.max(np.abs(derr))) if derr.size else None,
            "distance_error_bias": float(np.mean(derr)) if derr.size else None,
            "lateral_error_mean_abs": float(np.mean(np.abs(lerr))) if lerr.size else None,
            "first_alarm_frame": self.first_alarm_frame,
            "ego_speed_sources": dict(sorted(self.ego_speed_sources.items())),
            "n_accumulated_mean": float(np.mean(self.n_accumulated)) if self.n_accumulated else None,
            "per_class_bin_counts": {c: dict(sorted(bins.items(), key=lambda kv: _bin_order(kv[0])))
                                     for c, bins in sorted(self.per_class_bin.items())},
        }


COMPARISON_ROWS = [
    # (label, key, format, delta?)
    ("frames", "frames", "{:d}", True),
    ("alarm frames", "alarm_frames", "{:d}", True),
    ("alarm events", "alarm_events", "{:d}", True),
    ("advisory frames", "advisory_frames", "{:d}", True),
    ("first alarm frame", "first_alarm_frame", "{:d}", True),
    ("alarm distance min (m)", "alarm_distance_min", "{:.1f}", True),
    ("alarm distance max (m)", "alarm_distance_max", "{:.1f}", True),
    ("latency mean (ms)", "latency_ms_mean", "{:.1f}", True),
    ("latency p95 (ms)", "latency_ms_p95", "{:.1f}", True),
    ("latency max (ms)", "latency_ms_max", "{:.1f}", True),
    ("fp frames", "fp_frames", "{:d}", True),
    ("fp events", "fp_events", "{:d}", True),
    ("recall", "recall", "{:.1%}", False),
    ("frames merged (mean)", "n_accumulated_mean", "{:.2f}", True),
]


def format_comparison(summaries: Sequence[dict], names: Optional[Sequence[str]] = None) -> str:
    """Markdown before/after table of several ``Evaluation.summary()`` dicts (one column per
    summary; with exactly two, a delta column). ``names`` default to the ``file`` key."""
    import os
    if names is None:
        paths = [str(s.get("file", f"run {i + 1}")) for i, s in enumerate(summaries)]
        names = [os.path.basename(p) for p in paths]
        if len(set(names)) < len(names):        # same file name in different directories: keep the parent
            names = [os.path.basename(os.path.dirname(p)) + "/" + os.path.basename(p) for p in paths]
    two = len(summaries) == 2

    def cell(v, fmt):
        if v is None:
            return "n/a"
        return fmt.format(int(v) if fmt == "{:d}" else v)

    def delta(a, b, fmt):
        if a is None or b is None:
            return ""
        d = b - a
        if fmt == "{:d}":
            return f"{int(d):+d}"
        if fmt == "{:.1%}":
            return f"{d:+.1%}"
        return f"{d:+.1f}" if fmt == "{:.1f}" else f"{d:+.2f}"

    head = "| metric | " + " | ".join(names) + (" | delta |" if two else " |")
    sep = "|---|" + "---|" * len(names) + ("---|" if two else "")
    lines = [head, sep]
    for label, key, fmt, with_delta in COMPARISON_ROWS:
        vals = [s.get(key) for s in summaries]
        if all(v is None for v in vals):
            continue
        row = f"| {label} | " + " | ".join(cell(v, fmt) for v in vals)
        if two:
            row += " | " + (delta(vals[0], vals[1], fmt) if with_delta else "") + " |"
        else:
            row += " |"
        lines.append(row)
    caveats = [s.get("stride_caveat") for s in summaries if s.get("stride_caveat")]
    if caveats:
        lines.append("")
        lines.append("CAVEAT: " + caveats[0])
    return "\n".join(lines)


def format_summary(s: dict) -> str:
    """Human-readable block for ``resense summarize`` / ``resense eval``."""
    def f(v, fmt="{:.2f}"):
        return "n/a" if v is None else fmt.format(v)
    lines = [
        f"frames            : {s['frames']} (empty: {s['empty_frames']})" +
        (f", every {s['frame_stride']}th bag frame" if (s.get("frame_stride") or 1) > 1 else ""),
        f"alarm frames      : {s['alarm_frames']}   alarm events (distinct confirmed ids): {s['alarm_events']}",
        f"advisory frames   : {s['advisory_frames']} ({f(s['advisory_frame_rate'], '{:.1%}')} of frames)",
        f"alarm distance    : {f(s['alarm_distance_min'], '{:.1f}')} .. {f(s['alarm_distance_max'], '{:.1f}')} m",
        f"latency total ms  : mean {f(s['latency_ms_mean'], '{:.1f}')} / p95 {f(s['latency_ms_p95'], '{:.1f}')} / max {f(s['latency_ms_max'], '{:.1f}')}",
        f"bag time span     : {f(s['bag_time_s'], '{:.1f}')} s" +
        (f", travelled {s['distance_km']:.3f} km" if s.get("distance_km") is not None else ""),
        f"false alarms      : {s['fp_frames']} frames, {s['fp_events']} events, "
        f"{f(s['fp_events_per_hour'], '{:.1f}')} events/hour, {f(s['fp_events_per_km'], '{:.2f}')} events/km",
    ]
    if s.get("first_alarm_frame") is not None:
        lines.append(f"first alarm frame : {s['first_alarm_frame']}")
    if s.get("ego_speed_sources"):
        acc = s.get("n_accumulated_mean")
        lines.append("ego speed source  : " + ", ".join(f"{k} {v}" for k, v in s["ego_speed_sources"].items()) +
                     (f"; frames merged (mean) {acc:.2f}" if acc is not None else ""))
    if s.get("recall") is not None:
        lines.append(f"recall            : {s['recall']:.1%} ({s['per_bin_counts']})")
        if s.get("recall_by_class"):
            lines.append("recall by class   : " + ", ".join(f"{k} {f(v, '{:.0%}')}" for k, v in s["recall_by_class"].items()))
        for cls, bins in (s.get("per_class_bin_counts") or {}).items():
            lines.append(f"  {cls:15s}: " + ", ".join(f"{b} {v[0]}/{v[1]}" for b, v in bins.items()))
        if s.get("first_detection_distance"):
            fd = s["first_detection_distance"]
            lines.append("first detection   : " + ", ".join(f"{k} {v:.1f} m" for k, v in sorted(fd.items())))
        if s.get("distance_error_mean_abs") is not None:
            lines.append(f"distance error    : mean |err| {s['distance_error_mean_abs']:.2f} m, max {s['distance_error_max_abs']:.2f} m, "
                         f"bias {s['distance_error_bias']:+.2f} m; lateral mean |err| {f(s.get('lateral_error_mean_abs'))} m")
    if s.get("stride_caveat"):
        lines.append(f"CAVEAT            : {s['stride_caveat']}")
    return "\n".join(lines)
