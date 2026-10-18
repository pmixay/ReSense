"""Rejected raw-geometry hypothesis; this script does not replay a changed detector."""

import json
import hashlib
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, "/home/resense/data/n6/source_745096f")
from resense.track import TrackModel
from resense.farrails import FarRailParams, far_rails

p = Path(__file__).resolve().parent
d = json.loads((p / "exact_source_rail_support.json").read_text())
rows = []
for r in d["rows"]:
    i = r["frame"]
    a = np.load(f"/home/resense/data/decoded/synthetic_platform/f_{i:05d}.npz")
    raw = a["xyz"]
    xyz = np.c_[-raw[:, 1], raw[:, 0], raw[:, 2]]
    ring = a["ring"]
    ref = np.load(
        f"/home/resense/data/decoded/cloud_with_fake_obj/f_{i + 1195:05d}.npz"
    )["xyz"]
    source = {v.tobytes() for v in ref}
    keep = np.array([v.tobytes() in source for v in raw])
    m = TrackModel(**r["pre_extension_model"])
    anchor = r["variants"]["synthetic"]["near_seed"]
    out = {}
    for name, points, rings in [
        ("synthetic", xyz, ring),
        ("removed", xyz[keep], ring[keep]),
    ]:
        pars = FarRailParams(
            x_max=80,
            gauge=1.59,
            height_band=0.15,
            cant=0.1,
            max_gap=10,
            min_stations=3,
            pair_max_forward_gap=5,
            pair_use_nearer_forward=True,
        )
        rr = far_rails(points, rings, m, anchor, pars)
        x = rr.x[rr.x > 30]
        valid = (
            len(x) >= 3
            and len(np.unique(np.floor(x))) >= 3
            and np.ptp(x) >= 5
            and not np.any(abs(rr.y - m.center_y(rr.x)) > 0.1)
        )
        support = float(max(x)) if valid and max(x) + 15 > m.axis_valid else 0
        out[name] = {
            "support": support,
            "x": rr.x.tolist(),
            "residual": (rr.y - m.center_y(rr.x)).tolist(),
        }
    rows.append(
        {
            "frame": i,
            "v3_support": r["variants"]["synthetic"]["rail_axis_support"],
            **out,
        }
    )
summary = {
    "scope": "Exploratory raw geometry only on previously supported frames; no modified detector or STOP scoring. Not complete candidate evaluation.",
    "supported_before": len(rows),
    "narrow_supported": sum(r["synthetic"]["support"] > 0 for r in rows),
    "lost_frames": [r["frame"] for r in rows if not r["synthetic"]["support"]],
    "source_disagreement_frames": [
        r["frame"]
        for r in rows
        if abs(r["synthetic"]["support"] - r["removed"]["support"]) > 1e-7
    ],
    "first_person_228": next(r for r in rows if r["frame"] == 228),
    "conjunction_disagreement_frames": [
        r["frame"]
        for j, r in enumerate(rows)
        if abs(
            min(
                r["synthetic"]["support"],
                d["rows"][j]["variants"]["synthetic"]["rail_axis_support"],
            )
            - min(
                r["removed"]["support"],
                d["rows"][j]["variants"]["exact_new_returns_removed"][
                    "rail_axis_support"
                ],
            )
        )
        > 1e-7
    ],
    "source_probe_sha256": hashlib.sha256(
        (p / "exact_source_rail_support.json").read_bytes()
    ).hexdigest(),
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "disposition": "Rejected for default activation: narrower evidence hides the farther conflicting station, and retaining the original broad veto in conjunction still leaves object-dependent range support.",
    "rows": rows,
}
(p / "exploratory_height_band.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "rows"}))
