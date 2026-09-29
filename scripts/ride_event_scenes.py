#!/usr/bin/env python3
"""Inventory every ride false-STOP event and render cloud views for manual scene review.

  python scripts/ride_event_scenes.py --run out/gate --cache DATA/cache/new_data --out out/scenes

Scenes stay ``unreviewed`` until a person or reviewer inspects the clouds. Detector reason
codes are not scene labels. Events are (replay piece, track ID), matching the regression gate;
alarm frames and STOP episodes are counted separately. Input must cover the complete ride.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.cache_io import cache_file_stem, cache_files, load_cache_array  # noqa: E402
from resense.config import SensorConfig  # noqa: E402
from resense.frame import frame_from_compact  # noqa: E402
from resense.io import _natural_key  # noqa: E402


def collect(paths):
    events, frames, alarm_frames, episodes = {}, 0, 0, 0
    identities = set()
    for path in paths:
        previous = False
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                identity = row["frame_id"]
                if identity in identities:
                    raise ValueError(f"duplicate ride frame: {identity}")
                identities.add(identity)
                frames += 1
                stop = bool(row["obstacle"])
                alarm_frames += stop
                episodes += stop and not previous
                previous = stop
                for detection in row["detections"] if stop else []:
                    key = f"{Path(path).name}:{detection['id']}"
                    event = events.setdefault(key, {"key": key, "piece": Path(path).name,
                                                    "track_id": detection["id"], "hits": []})
                    event["hits"].append({"frame_id": identity, "distance_m": detection["distance"],
                                          "center": detection["center"], "stamp": row["stamp"]})
    out = []
    for i, event in enumerate(events.values(), 1):
        hits = event["hits"]
        out.append({**event, "number": i, "alarm_frames": len(hits),
                    "representative_frame": hits[len(hits) // 2]["frame_id"],
                    "distance_m": [min(h["distance_m"] for h in hits), max(h["distance_m"] for h in hits)],
                    "scene": "unreviewed", "confidence": None, "review_note": None})
    return {"frames": frames, "alarm_frames": alarm_frames, "stop_episodes": episodes,
            "alarm_events": len(out), "events": out}


def cache_index(directory):
    """Index either raw NPY or zstd-compressed NPY cache files by frame ID."""
    return {cache_file_stem(path): path for path in cache_files(str(directory))}


def render(inventory, cache, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    frames = cache_index(cache)
    for page in range((len(inventory["events"]) + 5) // 6):
        events = inventory["events"][page * 6:page * 6 + 6]
        fig, axes = plt.subplots(len(events), 3, figsize=(18, 3.6 * len(events)), squeeze=False)
        for row, event in enumerate(events):
            frame_id = event["representative_frame"]
            if frame_id not in frames:
                raise FileNotFoundError(f"no cached frame for event representative {frame_id}")
            frame = frame_from_compact(load_cache_array(frames[frame_id]), SensorConfig())
            xyz = frame.xyz
            # Deterministic thinning is only for presentation; scoring never reads these views.
            p = xyz[(xyz[:, 0] > 2) & (xyz[:, 0] < 180) & (np.abs(xyz[:, 1]) < 9)][::3]
            ax = axes[row, 0]
            low = p[(p[:, 2] > -2.5) & (p[:, 2] < 1.5)]
            ax.scatter(low[:, 0], low[:, 1], c=low[:, 2], s=0.2, cmap="viridis", vmin=-2.5, vmax=1.5)
            ax.set(xlim=(0, 180), ylim=(-8, 8), xlabel="X forward, m", ylabel="Y left, m")
            ax.set_title(f"{event['number']}. {event['key']}\n{event['representative_frame']}; STOP {event['distance_m']} m")
            ax = axes[row, 1]
            near = xyz[(xyz[:, 0] >= 3) & (xyz[:, 0] <= 20) & (np.abs(xyz[:, 1]) < 7)][::3]
            ax.scatter(near[:, 1], near[:, 2], c=near[:, 0], s=0.25, cmap="viridis", vmin=3, vmax=20)
            ax.set(xlim=(-7, 7), ylim=(-3, 5), xlabel="Y left, m", ylabel="Z up, m",
                   title="Near cross-section, X 3–20 m")
            ax = axes[row, 2]
            az = np.degrees(np.arctan2(p[:, 1], p[:, 0]))
            el = np.degrees(np.arctan2(p[:, 2], np.hypot(p[:, 0], p[:, 1])))
            ax.scatter(az, el, c=p[:, 0], s=0.3, cmap="plasma", vmin=3, vmax=120)
            ax.set(xlim=(45, -45), ylim=(-25, 35), xlabel="Azimuth, degrees", ylabel="Elevation, degrees",
                   title="Sensor view, color = range")
            for ax in axes[row]:
                ax.grid(alpha=0.15)
        fig.suptitle("Ride false STOP review — sensor coordinates; scene labels require visual inspection", fontsize=15)
        fig.tight_layout(rect=(0, 0, 1, 0.985))
        target = Path(out) / f"contact_{page + 1:02d}.png"
        fig.savefig(target, dpi=125)
        plt.close(fig)
        print(target, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    paths = sorted(Path(args.run).glob("new_data_*.jsonl"), key=lambda p: _natural_key(str(p)))
    inventory = collect(paths)
    if inventory["frames"] != 11271:
        raise SystemExit(f"incomplete ride: {inventory['frames']}/11271 frames")
    inventory["source_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    inventory["method"] = "Each event is one replay piece/track ID. Midpoint STOP cloud rendered for manual scene review."
    inventory["limitations"] = ["Scene appearance is separate from the cause of an alarm.",
                                 "Ambiguous scenes remain uncertain; no scene labels come from detector reason codes.",
                                 "Per-scene event-frame totals can overlap when several events share a frame."]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    render(inventory, args.cache, out)


if __name__ == "__main__":
    main()
