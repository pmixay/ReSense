#!/usr/bin/env python3
"""Reviewer script (own, not the author's): replay P4's 98 archived flipped-cluster snapshots through
``resense.lowobj.rail_reference_check`` of a given checkout and record the decision.

Input: the extracted ``trace_fix`` archive (docs/evidence/f1a_acceptance_2026-10-20/out/trace_fix_records.tar.xz):
per cluster a record (.fix.ndjson: bbox, tops, references, flags A/D of the B1-repair trace) and an .npz with the
raw returns near the cluster (X, dy, h, own = the cluster's indices, free = the low-free mask).

For every snapshot the production function is called on the production arrays (the cluster is rebuilt from the
record; nothing is re-implemented). Two runs per checkout: plain, and with a read-only wrapper around
``_rail_surface_reference`` that records whether and with what result the new branch was reached (the branch that
actually fired). The two runs must agree.

    RESENSE_REPO=<checkout> python snap_replay.py --snap <extracted trace_fix dir> --out <json>
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--snap", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--pad", type=float, default=0.0,
                help="widen the record's bbox (rounded to 1 mm in the archive) by this much on every side")
a = ap.parse_args()
ROOT = os.environ["RESENSE_REPO"]
sys.path.insert(0, ROOT)

from resense import lowobj  # noqa: E402
from resense.clustering import Cluster  # noqa: E402
from resense.config import LowObjectConfig  # noqa: E402

CFG = LowObjectConfig()
SPACING = 1.59


def build(row, own):
    bmin, bmax = np.array(row["bbox"][0], float) - a.pad, np.array(row["bbox"][1], float) + a.pad
    return Cluster(points_idx=np.flatnonzero(own), n=row["n"], n_raw=row["n"],
                   centroid=np.array(row["centroid"], float), bbox_min=bmin, bbox_max=bmax,
                   distance=row["d"], lateral=row["lat"], height_min=0.0, height_max=row["top_old"],
                   intensity=10.0, n_expected=5.0, score=1.0, zone="gauge", n_gauge=row["n"], kind="low")


def main():
    folder = Path(a.snap)
    has_surface = hasattr(lowobj, "_rail_surface_reference")
    orig_surface = getattr(lowobj, "_rail_surface_reference", None)
    trace = {}

    if has_surface:
        def wrapped(c, X, dy, h, d0, d1, cfg, spacing):
            r = orig_surface(c, X, dy, h, d0, d1, cfg, spacing)
            trace["reached"] = True
            trace["surface"] = r
            return r
        lowobj._rail_surface_reference = wrapped

    out = []
    for path in sorted(folder.glob("*.fix.ndjson")):
        piece = path.name.removesuffix(".fix.ndjson")
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if not row["A"] or row["D"]:
                continue
            dump = folder / f"{piece}_fix" / f"{row['stem']}_{row['k']}.npz"
            with np.load(dump) as z:
                X, dy, h, own, free = (z[k] for k in ("X", "dy", "h", "own", "free"))
            X, dy, h = X.astype(np.float64), dy.astype(np.float64), h.astype(np.float64)
            # plain run
            if has_surface:
                lowobj._rail_surface_reference = orig_surface
            c = build(row, own)
            kept_plain = lowobj.rail_reference_check([c], X, dy, h, CFG, SPACING, free)
            # traced run (read-only wrapper)
            if has_surface:
                lowobj._rail_surface_reference = wrapped
            trace.clear()
            c2 = build(row, own)
            kept_traced = lowobj.rail_reference_check([c2], X, dy, h, CFG, SPACING, free)
            if has_surface:
                lowobj._rail_surface_reference = orig_surface
            assert bool(kept_plain) == bool(kept_traced), "instrumentation changed the result"
            out.append(dict(piece=piece, stem=row["stem"], k=row["k"], d=row["d"], lat=row["lat"],
                            width=row["size"][1], top_old=row["top_old"], top_new=row["top_new"],
                            ref_orig=row["ref_orig"], ref_ind=row["ref_ind"], rec_A=row["A"], rec_D=row["D"],
                            rec_cause=row["cause"], rejected=bool(kept_plain),
                            surface_branch_reached=bool(trace.get("reached", False)),
                            surface=trace.get("surface"), n_own=int(own.sum()), n_pts=int(X.size)))
    Path(a.out).write_text(json.dumps(dict(repo=ROOT, has_surface=has_surface, rows=out), indent=1) + "\n")
    print(ROOT, "rows", len(out), "rejected", sum(r["rejected"] for r in out),
          "surface branch reached", sum(r["surface_branch_reached"] for r in out))


if __name__ == "__main__":
    main()
