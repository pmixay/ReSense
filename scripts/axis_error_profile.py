"""Axis error, frame-to-frame jitter and point counts by range, from the labels of
``cloud_with_fake_obj`` alone (no bag, no detector run).

The organizers' ten synthetic objects stand still in the tunnel while the train approaches them,
so each object keeps one place relative to the track. Its ``lateral`` in the label file is measured
from the per-frame track axis of the shipped detector (``scripts/label_fake_objects.py``,
``estimate_track``: the raw per-frame fit, before the live node's temporal smoothing). Hence:

* axis error at range d: ``|lateral(d) - median lateral at 8-25 m|`` (near range = the axis is
  reliable there). Part of it is the organizers' own placement drift (they say the synthetic
  objects "float" along the track), so it is an upper estimate of the axis error;
* jitter: ``|lateral(t+1) - lateral(t)|`` of one object in consecutive frames (smooth placement
  drift hardly contributes): how much the far gauge edge moves per frame (10 Hz) before smoothing;
* points: the median ``n_points`` of each object by range (what a detector has to work with).

Usage::

    python scripts/axis_error_profile.py                      # markdown tables on stdout
    python scripts/axis_error_profile.py --json out.json      # also the raw numbers

Standard library only. Findings: ``docs/evidence/axis_profile_2026-10-16/README.md``.
"""

from __future__ import annotations

import argparse
import itertools
import json
import statistics
import sys
from pathlib import Path

DEFAULT_LABELS = Path(__file__).resolve().parents[1] / "labels" / "cloud_with_fake_obj.json"
DEFAULT_BINS = ((200.0, 260.0), (150.0, 200.0), (120.0, 150.0), (100.0, 120.0), (80.0, 100.0),
                (60.0, 80.0), (40.0, 60.0), (25.0, 40.0))
NEAR_RANGE = (8.0, 25.0)


def load_tracks(labels: dict) -> dict[str, list[tuple[int, dict]]]:
    """``{object name: [(frame, label entry), ...]}`` in frame order (``_meta`` skipped)."""
    tracks: dict[str, list[tuple[int, dict]]] = {}
    for key in sorted(k for k in labels if k != "_meta"):
        for entry in labels[key]:
            tracks.setdefault(entry["name"], []).append((int(key), entry))
    return tracks


def quantile(sorted_values: list[float], p: float) -> float:
    return sorted_values[min(len(sorted_values) - 1, int(p * len(sorted_values)))]


def summarize(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    v = sorted(values)
    return {"n": len(v), "median": statistics.median(v), "p75": quantile(v, 0.75),
            "p90": quantile(v, 0.90), "max": v[-1]}


def _bin_of(distance: float, bins) -> tuple | None:
    for b in bins:
        if b[0] <= distance < b[1]:
            return b
    return None


def axis_error_by_range(tracks, bins=DEFAULT_BINS, near=NEAR_RANGE, min_near=5) -> dict:
    """Pooled ``|lateral(d) - near reference|`` per range bin; objects with too few near frames
    (< ``min_near``) are skipped."""
    out: dict[tuple, list[float]] = {b: [] for b in bins}
    for entries in tracks.values():
        ref = [e["lateral"] for _, e in entries if near[0] <= e["distance"] <= near[1]]
        if len(ref) < min_near:
            continue
        ref_lat = statistics.median(ref)
        for _, e in entries:
            b = _bin_of(e["distance"], bins)
            if b is not None:
                out[b].append(abs(e["lateral"] - ref_lat))
    return {b: summarize(v) for b, v in out.items()}


def jitter_by_range(tracks, bins=DEFAULT_BINS) -> dict:
    """Pooled ``|lateral(t+1) - lateral(t)|`` of consecutive frames per range bin (of the later frame)."""
    out: dict[tuple, list[float]] = {b: [] for b in bins}
    for entries in tracks.values():
        for (f0, a), (f1, b_) in itertools.pairwise(entries):
            if f1 - f0 != 1:
                continue
            b = _bin_of(b_["distance"], bins)
            if b is not None:
                out[b].append(abs(b_["lateral"] - a["lateral"]))
    return {b: summarize(v) for b, v in out.items()}


def points_by_range(tracks, bins=DEFAULT_BINS) -> dict:
    """``{object name: {bin: median n_points}}`` (empty bins omitted)."""
    out: dict[str, dict[tuple, int]] = {}
    for name, entries in tracks.items():
        per_bin: dict[tuple, list[int]] = {}
        for _, e in entries:
            b = _bin_of(e["distance"], bins)
            if b is not None and "n_points" in e:
                per_bin.setdefault(b, []).append(int(e["n_points"]))
        out[name] = {b: int(statistics.median(v)) for b, v in per_bin.items()}
    return out


def _label(b: tuple) -> str:
    return f"{b[0]:.0f}-{b[1]:.0f} m"


def markdown(axis: dict, jitter: dict, points: dict, bins=DEFAULT_BINS) -> str:
    lines = ["| range | n | axis error median (m) | p75 | p90 | max | jitter median (m/frame) | p90 | max |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for b in bins:
        a, j = axis[b], jitter[b]
        if not a.get("n"):
            continue
        jm = f"{j['median']:.3f} | {j['p90']:.3f} | {j['max']:.3f}" if j.get("n") else "- | - | -"
        lines.append(f"| {_label(b)} | {a['n']} | {a['median']:.2f} | {a['p75']:.2f} | {a['p90']:.2f} "
                     f"| {a['max']:.2f} | {jm} |")
    lines += ["", "| object | " + " | ".join(_label(b) for b in bins) + " |",
              "|---|" + "---:|" * len(bins)]
    for name, per_bin in points.items():
        lines.append(f"| {name} | " + " | ".join(str(per_bin.get(b, "")) for b in bins) + " |")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    ap.add_argument("--json", type=Path, default=None, help="also write the raw numbers here")
    args = ap.parse_args(argv)
    labels = json.loads(args.labels.read_text(encoding="utf-8"))
    tracks = load_tracks(labels)
    axis, jitter, points = axis_error_by_range(tracks), jitter_by_range(tracks), points_by_range(tracks)
    print(markdown(axis, jitter, points))
    if args.json:
        def key(d):
            return {_label(b): v for b, v in d.items()}
        args.json.write_text(json.dumps({"axis_error": key(axis), "jitter": key(jitter),
                                         "points": {n: key(p) for n, p in points.items()}},
                                        indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
