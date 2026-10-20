#!/usr/bin/env python3
"""Keep every raw point F1a can read, preserving indices and checking full-state parity."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from resense.config import LowObjectConfig
from resense.lowobj import local_rail_reference, low_free_mask, rail_reference_check


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("destination", type=Path)
    a = ap.parse_args()
    a.destination.mkdir(exist_ok=False)
    cfg = LowObjectConfig()
    manifest = []
    for path in sorted(a.source.glob("frame_*.npz")):
        with np.load(path) as data:
            X, dy, h = (data[k] for k in ("X", "dy", "h"))
            keep = np.zeros(X.size, bool)
            clusters = []
            payload = {k: data[k] for k in data.files if k.startswith("state_")}
            for key in payload:
                s, idx = data[key], data["idx_" + key.removeprefix("state_")]
                clusters.append(SimpleNamespace(points_idx=idx, kind="low", bbox_min=s[:3], bbox_max=s[3:6],
                    lateral=s[6], height_max=s[7], low_height_weak=bool(s[8]),
                    zone="gauge" if s[9] else "warning", reason="captured_reason" if s[10] else ""))
                if idx.size:
                    d = dy[idx]
                    rail_band = (((dy >= -0.795 - 0.1) & (dy <= -0.795 + 0.1))
                                 | ((dy >= 0.795 - 0.1) & (dy <= 0.795 + 0.1)))
                    keep |= ((X >= s[0] - 5) & (X < s[3] + 5) & rail_band
                             & (h > -0.3) & (h < 0.3))
                    keep |= (X >= s[0]) & (X <= s[3]) & (dy >= d.min()) & (dy <= d.max()) & (h < cfg.foot_max_top)
                    keep[idx] = True
            selected = np.flatnonzero(keep)
            mapped = np.full(X.size, -1, int)
            mapped[selected] = np.arange(selected.size)
            compact = [SimpleNamespace(**{**vars(c), "points_idx": mapped[c.points_idx]}) for c in clusters]
            for prefix, cs, xx, dd, hh in (("full", clusters, X, dy, h),
                                          ("compact", compact, X[keep], dy[keep], h[keep])):
                refs = [local_rail_reference(c, xx, dd, hh, cfg, 1.59) for c in cs]
                rejected = rail_reference_check(cs, xx, dd, hh, cfg, 1.59, low_free_mask(xx.size, cs, xx, dd))
                signature = (refs, [i for i, c in enumerate(cs) if any(c is r for r in rejected)])
                if prefix == "full":
                    expected = signature
                else:
                    assert signature == expected, path
            payload.update(X=X[keep], dy=dy[keep], h=h[keep], original_point_index=selected)
            payload.update({"idx_" + key.removeprefix("state_"): mapped[data["idx_" + key.removeprefix("state_")]]
                            for key in payload if key.startswith("state_")})
            dest = a.destination / path.name
            np.savez_compressed(dest, **payload)
            manifest.append({"frame": path.name, "full_points": int(X.size), "kept_points": int(selected.size),
                             "full_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                             "compact_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(), "exact_rule_parity": True})
    (a.destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(len(manifest), "full/compact rule states identical")


if __name__ == "__main__":
    main()
