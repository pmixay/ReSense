"""Per-run aggregates: compact chart series, decision episodes, events and the RunSummary.

Pure functions over the ``/frames`` dicts (FrameResult.to_dict() + frame, t, decision, pos), so
the worker, the jsonl import and the tests share them."""
from __future__ import annotations

from typing import Any, Iterable, Sequence

import numpy as np

from resense_web.decision import DECISIONS, FROM_LETTER, LETTER, letter_of


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if np.isfinite(f) else None


class SeriesBuilder:
    """Accumulates the per-frame arrays of ``GET /runs/{id}/series`` one frame at a time."""

    def __init__(self) -> None:
        self.frame: list[int] = []
        self.t: list[float] = []
        self.letters: list[str] = []
        self.nearest: list[float | None] = []
        self.clear: list[float] = []
        self.latency_ms: list[float] = []
        self.n_detections: list[int] = []
        self.n_warnings: list[int] = []
        self.n_points: list[int] = []
        self.visibility: list[float | None] = []

    def __len__(self) -> int:
        return len(self.letters)

    def add(self, d: dict) -> None:
        self.frame.append(int(d.get("frame", len(self.frame))))
        self.t.append(round(_num(d.get("t")) or 0.0, 3))
        self.letters.append(letter_of(d.get("decision", "GO")))
        nd = _num(d.get("nearest_distance"))
        self.nearest.append(None if nd is None else round(nd, 2))
        self.clear.append(round(_num(d.get("clear_distance")) or 0.0, 1))
        timing = d.get("timing_ms") or {}
        self.latency_ms.append(round(_num(timing.get("total")) or 0.0, 2))
        self.n_detections.append(len(d.get("detections") or []))
        self.n_warnings.append(len(d.get("warnings") or []))
        self.n_points.append(int(_num(d.get("n_points")) or 0))
        vis = _num((d.get("health") or {}).get("visibility"))
        self.visibility.append(None if vis is None else round(vis, 1))

    @property
    def decisions(self) -> str:
        return "".join(self.letters)

    def series(self, labels_in_gauge: Sequence[bool] | None = None) -> dict:
        return {
            "frame": self.frame, "t": self.t, "decisions": self.decisions, "nearest": self.nearest,
            "clear": self.clear, "latency_ms": self.latency_ms, "n_detections": self.n_detections,
            "n_warnings": self.n_warnings, "n_points": self.n_points, "visibility": self.visibility,
            "labels_in_gauge": None if labels_in_gauge is None else [bool(x) for x in labels_in_gauge],
        }

    @classmethod
    def from_frames(cls, frames: Iterable[dict]) -> "SeriesBuilder":
        b = cls()
        for d in frames:
            b.add(d)
        return b


def episodes_of(frames: Sequence[int], t: Sequence[float], decisions: str,
                nearest: Sequence[float | None]) -> list[dict]:
    """Maximal blocks of consecutive processed frames with one decision."""
    out: list[dict] = []
    n = len(decisions)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and decisions[j + 1] == decisions[i]:
            j += 1
        dec = FROM_LETTER.get(decisions[i], "FAULT")
        dmin = dmax = None
        if dec == "STOP":
            ds = [nearest[k] for k in range(i, j + 1) if nearest[k] is not None]
            if ds:
                dmin, dmax = round(min(ds), 2), round(max(ds), 2)
        out.append({"decision": dec, "first_frame": int(frames[i]), "last_frame": int(frames[j]),
                    "t0": round(float(t[i]), 3), "t1": round(float(t[j]), 3), "n_frames": j - i + 1,
                    "distance_min": dmin, "distance_max": dmax})
        i = j + 1
    return out


def _stop_on_side(episodes: Sequence[dict], k: int, step: int) -> bool:
    """A STOP episode is reached from episode ``k`` in direction ``step`` without crossing a GO."""
    j = k + step
    while 0 <= j < len(episodes):
        d = episodes[j]["decision"]
        if d == "STOP":
            return True
        if d == "GO":
            return False
        j += step
    return False


def events_of(episodes: Sequence[dict]) -> list[dict]:
    """Non-GO episodes, plus GO gaps inside a STOP (a STOP on both sides with only CAUTION /
    FAULT in between): the dropouts a jury should see."""
    out = []
    for k, ep in enumerate(episodes):
        if ep["decision"] != "GO" or (_stop_on_side(episodes, k, -1) and _stop_on_side(episodes, k, 1)):
            out.append(ep)
    return out


def _pct(values: Sequence[float], q: float) -> float:
    return round(float(np.percentile(np.asarray(values, dtype=float), q)), 2) if len(values) else 0.0


def run_summary(series: SeriesBuilder, processing_fps: float, eval_summary: dict | None = None,
                episodes: Sequence[dict] | None = None) -> dict:
    n = len(series)
    decisions = series.decisions
    if episodes is None:
        episodes = episodes_of(series.frame, series.t, decisions, series.nearest)
    counts = {d: decisions.count(LETTER[d]) for d in DECISIONS}
    first_stop = None
    stop_dist = []
    for i, c in enumerate(decisions):
        if c != "S":
            continue
        if first_stop is None:
            first_stop = {"frame": series.frame[i], "t": series.t[i], "distance": series.nearest[i]}
        if series.nearest[i] is not None:
            stop_dist.append(series.nearest[i])
    vis = [v for v in series.visibility if v is not None]
    return {
        "n_frames": n,
        "duration_s": round(series.t[-1] - series.t[0], 3) if n else 0.0,
        "counts": counts,
        "decisions": decisions,
        "stop_episodes": sum(1 for e in episodes if e["decision"] == "STOP"),
        "first_stop": first_stop,
        "distance_min": round(min(stop_dist), 2) if stop_dist else None,
        "distance_max": round(max(stop_dist), 2) if stop_dist else None,
        "latency_ms": {"p50": _pct(series.latency_ms, 50), "p95": _pct(series.latency_ms, 95),
                       "max": round(max(series.latency_ms), 2) if n else 0.0},
        "processing_fps": round(float(processing_fps), 2),
        "clear_distance_median": round(float(np.median(series.clear)), 1) if n else None,
        "visibility_median": round(float(np.median(vis)), 1) if vis else None,
        "eval": eval_summary,
    }
