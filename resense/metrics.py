"""Evaluation: match detections against ground truth, recall vs range, false positives.

Two levels of false-alarm accounting (docs/EVALUATION.md section 2):

* **frames** — frames with ``obstacle = true`` that have no gauge ground truth (``fp_frames``);
* **events** — distinct confirmed gauge track ids (``detections[].id`` of the status JSON)
  that were never matched to a ground-truth object (``fp_events``). One object that stays
  in the corridor for 50 frames is one event; this is the headline number, reported per
  hour of bag time (from the ``stamp`` field) and per km when a speed is known (a constant
  ``speed_mps`` passed to :meth:`Evaluation.add_frame`, or a per-frame ``ego_speed_mps`` /
  ``ego_speed`` key in the result dict).

Frame indices (the ``frame`` key that ``resense run`` writes) are used to detect the
subsampling stride: with every N-th frame, ``tracking.confirm_hits`` consecutive hits are
``N * frame_dt`` seconds apart, so a candidate must persist ``confirm_hits * N * frame_dt``
seconds instead of ``confirm_hits * frame_dt`` -- subsampled false-alarm counts understate
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


def gt_objects(rows: Sequence[dict], skip_occluded: bool = True) -> List[GTObstacle]:
    """Rows of one frame -> GTObstacle list; rows with ``n_points == 0`` (object fully
    occluded by real geometry) are dropped when ``skip_occluded`` (they count separately)."""
    return [GTObstacle.from_dict(r) for r in rows if not (skip_occluded and r.get("n_points", 1) == 0)]


def match(det_distance: float, det_lateral: float, gt: GTObstacle,
          tol_base: float = 2.0, tol_rel: float = 0.03, lateral_tol: float = 1.0) -> bool:
    tol = max(tol_base, tol_rel * gt.distance) + 0.5 * max(gt.size[0], 0.0)
    return abs(det_distance - gt.distance) <= tol and abs(det_lateral - gt.lateral) <= lateral_tol


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
    confirm_hits: int = 3                  # tracking.confirm_hits, for the stride caveat
    frame_dt: float = 0.1                  # tracking.frame_dt (s)
    alarm_frames: int = 0                  # frames with obstacle = true (all frames)
    advisory_frames: int = 0               # frames with warning = true (all frames)
    alarm_ids: Set[int] = field(default_factory=set)      # confirmed gauge ids seen at all
    matched_ids: Set[int] = field(default_factory=set)    # ... matched to a gt object at least once
    unmatched_ids: Set[int] = field(default_factory=set)  # ... unmatched in at least one frame
    per_class: Dict[str, List[int]] = field(default_factory=dict)   # class: [tp, total]
    stamps: List[float] = field(default_factory=list)
    frame_indices: List[Optional[int]] = field(default_factory=list)
    alarm_distances: List[float] = field(default_factory=list)
    distance_m: float = 0.0                # travelled distance integrated from speed x stamp gaps
    speed_known: bool = False

    def add_frame(self, result_dict: dict, gts: Sequence[GTObstacle], use_candidates: bool = False,
                  speed_mps: Optional[float] = None, frame_index: Optional[int] = None) -> None:
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
        if not gauge_gts:
            self.n_empty_frames += 1
            if result_dict["obstacle"]:
                self.fp_frames += 1
        for g in gauge_gts:
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
            hit = False
            for i, d in enumerate(dets):
                if not used[i] and match(d["distance"], d["lateral"], g):
                    used[i] = True
                    hit = True
                    if "id" in d:
                        self.matched_ids.add(int(d["id"]))
                    break
            if hit:
                self.tp += 1
                self.per_bin[key][0] += 1
                self.per_class[cls_key][0] += 1
                self.first_detection[g.label] = max(self.first_detection.get(g.label, 0.0), g.distance)
            else:
                self.fn += 1
        self.fp_detections += int((~used).sum())
        for i, d in enumerate(dets):
            if "id" in d:
                self.alarm_ids.add(int(d["id"]))
                if not used[i]:
                    self.unmatched_ids.add(int(d["id"]))
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
        if stamp is not None:
            stamp = float(stamp)
            if speed_mps is not None and self.stamps:
                self.distance_m += float(speed_mps) * max(stamp - self.stamps[-1], 0.0)
            self.stamps.append(stamp)
        if speed_mps is not None:
            self.speed_known = True
        if frame_index is None:
            frame_index = result_dict.get("frame")
        self.frame_indices.append(None if frame_index is None else int(frame_index))

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
        return (max(self.stamps) - min(self.stamps)) if len(self.stamps) >= 2 else 0.0

    @property
    def stride(self) -> Optional[int]:
        return frame_stride([i for i in self.frame_indices if i is not None])

    def stride_caveat(self) -> Optional[str]:
        s = self.stride
        if s is None or s <= 1:
            return None
        return (f"frames are every {s}th bag frame: tracking.confirm_hits = {self.confirm_hits} consecutive "
                f"hits are {s * self.frame_dt:.1f} s apart, so a candidate must persist "
                f"{self.confirm_hits * s * self.frame_dt:.1f} s to be confirmed instead of "
                f"{self.confirm_hits * self.frame_dt:.1f} s at 10 Hz; subsampled alarm and false-alarm "
                f"counts understate the full-rate values (run every frame for the headline numbers)")

    def summary(self) -> dict:
        rec = {k: (v[0] / v[1] if v[1] else None) for k, v in sorted(self.per_bin.items(), key=lambda kv: float(kv[0].split("-")[0].rstrip("+")))}
        hours = self.bag_time_s / 3600.0
        km = self.distance_m / 1000.0
        lat = np.asarray(self.latency_ms, dtype=float)
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
            "fp_events_per_km": (self.fp_events / km) if (self.speed_known and km > 0) else None,
            "frame_stride": self.stride,
            "stride_caveat": self.stride_caveat(),
        }


def format_summary(s: dict) -> str:
    """Human-readable block for ``resense summarize`` / ``resense eval``."""
    def f(v, fmt="{:.2f}"):
        return "n/a" if v is None else fmt.format(v)
    lines = [
        f"frames            : {s['frames']} (empty: {s['empty_frames']})" +
        (f", every {s['frame_stride']}th bag frame" if s.get("frame_stride") else ""),
        f"alarm frames      : {s['alarm_frames']}   alarm events (distinct confirmed ids): {s['alarm_events']}",
        f"advisory frames   : {s['advisory_frames']} ({f(s['advisory_frame_rate'], '{:.1%}')} of frames)",
        f"alarm distance    : {f(s['alarm_distance_min'], '{:.1f}')} .. {f(s['alarm_distance_max'], '{:.1f}')} m",
        f"latency total ms  : mean {f(s['latency_ms_mean'], '{:.1f}')} / p95 {f(s['latency_ms_p95'], '{:.1f}')} / max {f(s['latency_ms_max'], '{:.1f}')}",
        f"bag time span     : {f(s['bag_time_s'], '{:.1f}')} s" +
        (f", travelled {s['distance_km']:.3f} km" if s.get("distance_km") is not None else ""),
        f"false alarms      : {s['fp_frames']} frames, {s['fp_events']} events, "
        f"{f(s['fp_events_per_hour'], '{:.1f}')} events/hour, {f(s['fp_events_per_km'], '{:.2f}')} events/km",
    ]
    if s.get("recall") is not None:
        lines.append(f"recall            : {s['recall']:.1%} ({s['per_bin_counts']})")
        if s.get("recall_by_class"):
            lines.append(f"recall by class   : " + ", ".join(f"{k} {f(v, '{:.0%}')}" for k, v in s["recall_by_class"].items()))
        if s.get("first_detection_distance"):
            fd = s["first_detection_distance"]
            lines.append("first detection   : " + ", ".join(f"{k} {v:.1f} m" for k, v in sorted(fd.items())))
    if s.get("stride_caveat"):
        lines.append(f"CAVEAT            : {s['stride_caveat']}")
    return "\n".join(lines)
