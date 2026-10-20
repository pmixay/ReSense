#!/usr/bin/env python3
"""Visual inspection: raw B1 fragments and the independently specified P4 box."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from physical import scene
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.lowobj import local_rail_reference, low_free_mask

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))
from test_f1_false_alarms import _long_object_on_the_left_rail  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    (X, dy, h), pieces = _long_object_on_the_left_rail()
    free = low_free_mask(X.size, pieces, X, dy)
    rail = np.abs(dy - 0.795) < 0.1
    axes[0].scatter(X[rail & free], h[rail & free], label="Independent rail returns", s=35)
    axes[0].scatter(X[rail & ~free], h[rail & ~free], label="Returns in six obstacle footprints", s=18)
    cfg = DetectorConfig()
    c = pieces[0]
    old = local_rail_reference(c, X, dy, h, cfg.lowobj, 1.59)
    independent = local_rail_reference(c, X[free], dy[free], h[free], cfg.lowobj, 1.59)
    axes[0].axhline(old + cfg.lowobj.local_rail_margin, color="red", ls="--", label="Old rejection threshold")
    axes[0].axhline(independent + cfg.lowobj.local_rail_margin, color="green", ls="--", label="Independent threshold")
    axes[0].set(xlim=(29, 47), ylim=(-0.02, 0.11), xlabel="Along track, m", ylabel="Height above rail model, m",
                title="B1: other fragments cannot be rail support")
    axes[0].legend(fontsize=8)
    fr, head = scene(0.18, 40, 0.17)
    det = Detector(cfg)
    for k in range(12):
        result = det.process(Frame(xyz=fr.xyz, intensity=fr.intensity, stamp=k * 0.1))
    points = fr.xyz
    select = ((points[:, 0] > 39.8) & (points[:, 0] < 40.5) & (np.abs(points[:, 1] - 0.25) < 0.25)
              & (points[:, 2] > -1.6) & (points[:, 2] < 0.0))
    axes[1].scatter(points[select, 1], points[select, 2], s=14, label="Raw first returns near box")
    model = float(det.track.rail_z(40))
    axes[1].axhline(head, color="blue", label="True raised rail head")
    axes[1].axhline(model + 0.12, color="red", ls="--", label="Low-stage input cap")
    axes[1].axhline(head + 0.17, color="green", label="True box top")
    axes[1].set(xlabel="Vehicle lateral, m", ylabel="Vehicle z, m", title="Capped-top B1: visible upper body")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(a.out, dpi=160)
    evidence = {"fragment_raw_reference": old, "fragment_independent_reference": independent,
                "physical_true_head_z": head, "physical_model_head_z": model,
                "physical_raw_examples": points[select][:12].tolist(),
                "physical_raw_points_in_window": int(select.sum()),
                "physical_detections": [d.to_dict() for d in result.detections]}
    a.out.with_suffix(".json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
