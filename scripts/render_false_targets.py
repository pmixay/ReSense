#!/usr/bin/env python3
"""Render exact false-target supports from trace_false_targets.py; no inference labels."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root, out = Path(args.trace).parent, Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads(Path(args.trace).read_text())
    by_key = {e["key"]: e for e in data["events"]}
    keys = [e["key"] for e in json.loads(Path(args.inventory).read_text())["events"]]
    selected = []
    for number, key in enumerate(keys, 1):
        event = by_key[key]
        choices = [r for r in event["timeline"] if r["alarm"] and not r["misses"] and "point_snapshot" in r]
        if not choices:
            raise ValueError(f"no actual matched alarm support for {key}")
        selected.append((number, event, choices[len(choices) // 2]))
    for start in range(0, len(selected), 5):
        group = selected[start:start + 5]
        fig, axes = plt.subplots(len(group), 4, figsize=(21, 3.4 * len(group)), squeeze=False)
        for row, (number, event, record) in enumerate(group):
            d = np.load(root / "points" / record["point_snapshot"])
            p, dy, h, t = d["xyz"], d["dy"], d["h"], d["target"]
            center = p[t].mean(axis=0)
            for ax in axes[row]:
                ax.grid(alpha=.2)
            ax = axes[row, 0]
            ax.scatter(p[:, 0], p[:, 1], c=h, s=1, cmap="viridis", vmin=-.5, vmax=4)
            ax.scatter(p[t, 0], p[t, 1], c="red", s=10)
            ax.set(xlabel="Physical X (m)", ylabel="Physical Y (m)",
                   title=f"{number}. {event['key']} / frame {record['piece_frame']}")
            ax = axes[row, 1]
            close = np.abs(p[:, 0] - center[0]) < 3
            ax.scatter(dy[close], h[close], c="gray", s=2)
            ax.scatter(dy[t], h[t], c="red", s=12)
            ax.plot([-1.05, 1.05, 1.05, -1.05, -1.05], [.12, .12, 3, 3, .12], c="orange")
            ax.set(xlim=(-4, 4), ylim=(-1, 6), xlabel="Model lateral (m)", ylabel="Model height (m)")
            ax = axes[row, 2]
            band = np.abs(dy - np.median(dy[t])) < .2
            ax.scatter(p[band, 0], h[band], c="gray", s=3)
            ax.scatter(p[t, 0], h[t], c="red", s=12)
            ax.axhline(0, c="orange")
            ax.set(xlabel="Physical X, same lateral band (m)", ylabel="Model height (m)", ylim=(-.4, 4))
            ax = axes[row, 3]
            matched = [r for r in event["timeline"] if not r["misses"]]
            for j, label in [(1, "Y bbox midpoint"), (2, "Z bbox midpoint")]:
                values = [(r["cluster"]["bbox_min"][j] + r["cluster"]["bbox_max"][j]) / 2 for r in matched]
                ax.plot([r["piece_frame"] for r in matched], values, ".-", ms=3, label=label)
            for r in event["timeline"]:
                if r["alarm"]:
                    ax.axvline(r["piece_frame"], color="red", alpha=.12)
            ax.set(xlabel="Piece frame (red = STOP)", ylabel="Physical coordinate (m)")
            ax.legend(fontsize=7)
        fig.suptitle("Exact matched target support = red; context = gray/color. Heights and lateral are fitted, not surveyed.\n"
                     "Physical XYZ use the mount-corrected sensor frame; calibration changes can rotate coordinates.", fontsize=11)
        fig.tight_layout(rect=(0, 0, 1, .96))
        fig.savefig(out / f"targets_{start // 5 + 1:02d}.png", dpi=120)
        plt.close(fig)


if __name__ == "__main__":
    main()
