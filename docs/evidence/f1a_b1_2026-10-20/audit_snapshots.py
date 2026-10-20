#!/usr/bin/env python3
"""Check F1a's direct decisions on captured actual pre-rule cluster states."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from resense.config import LowObjectConfig
from resense.lowobj import local_rail_reference, low_free_mask, rail_reference_check


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshots", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    cfg = LowObjectConfig()
    rows = []
    frames = 0
    for path in sorted(a.snapshots.glob("frame_*.npz")):
        with np.load(path) as d:
            frames += 1
            X, dy, h = (d[k] for k in ("X", "dy", "h"))
            clusters = []
            for key in d.files:
                if not key.startswith("state_"):
                    continue
                s, idx = d[key], d["idx_" + key.removeprefix("state_")]
                clusters.append(SimpleNamespace(points_idx=idx, kind="low", bbox_min=s[:3], bbox_max=s[3:6],
                    lateral=s[6], height_max=s[7], low_height_weak=bool(s[8]),
                    zone="gauge" if s[9] else "warning", reason="captured_reason" if s[10] else ""))
            free = low_free_mask(X.size, clusters, X, dy)
            actual = rail_reference_check(clusters, X, dy, h, cfg, 1.59, free)
            for i, c in enumerate(clusters):
                if c.low_height_weak or c.zone != "gauge" or c.reason or not c.points_idx.size:
                    continue
                original = local_rail_reference(c, X, dy, h, cfg, 1.59)
                old_weak = original is not None and c.height_max < original + cfg.local_rail_margin
                new_weak = any(c is cl for cl in actual)
                assert not new_weak or old_weak, (path, i)
                if old_weak:
                    d = dy[c.points_idx]
                    foot = ((X >= c.bbox_min[0]) & (X <= c.bbox_max[0]) & (dy >= d.min()) & (dy <= d.max())
                            & (h < cfg.foot_max_top))
                    full_top = max(float(c.height_max), float(h[foot].max())) if foot.any() else float(c.height_max)
                    independent = local_rail_reference(c, X[free], dy[free], h[free], cfg, 1.59)
                    refined = independent is not None and full_top < independent + cfg.local_rail_margin
                    rows.append({"frame": int(path.stem.removeprefix("frame_")), "cluster": i,
                                 "distance": float(c.bbox_min[0]), "lateral": float(c.lateral),
                                 "selected_top": float(c.height_max), "original_ref": original,
                                 "original_weak": bool(old_weak), "candidate_weak": new_weak,
                                 "full_top": full_top, "independent_ref": independent,
                                 "refined_decision_prediction": bool(refined)})
    # Positive control: both the old failure and repaired reference decisions must be exercised.
    assert rows and any(r["candidate_weak"] for r in rows)
    assert any(not r["candidate_weak"] for r in rows)
    # Known positive control for the proposed refinement: the selected top
    # was rejected, but the observed body exceeds only the original line.
    selected, original, observed, independent = 0.06, 0.075, 0.10, 0.15
    control_v2 = observed < min(original, independent) + cfg.local_rail_margin
    control_refined = (selected < original + cfg.local_rail_margin
                       and observed < independent + cfg.local_rail_margin)
    assert not control_v2 and control_refined
    report = {"frames": frames, "originally_rejected_clusters": len(rows),
              "retained_rejections": sum(r["candidate_weak"] for r in rows),
              "refined_predicted_rejections": sum(r["refined_decision_prediction"] for r in rows),
              "refinement_difference_rows": [r for r in rows if r["candidate_weak"] != r["refined_decision_prediction"]],
              "refinement_positive_control": {"candidate": control_v2, "refined": control_refined},
              "newly_weakened_clusters": 0, "rows": rows}
    a.out.write_text(json.dumps(report, indent=2) + "\n")
    print({k: v for k, v in report.items() if k != "rows"})


if __name__ == "__main__":
    main()
