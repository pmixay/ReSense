#!/usr/bin/env python3
"""Set F with a person lying on the track (EXPERIMENTS.md section 2d, 23.09).

Registers two synthetic objects - a 0.5 x 1.8 x 0.35 m box lying ``across`` the track and the
same box lying ``along`` it - and runs ``scripts/far_range_eval.py`` with them. With
``--bed-depth D`` the object's base is put D m below the model's rail level instead of on the bed
measured under it: the bed of the organizers' tunnels lies 0.26-0.34 m below the rail head beside
a 0.57-0.60 m central drainage trough, so D decides whether the body rises above the rail head.

    python scripts/lying_person_eval.py --cache /data/cache/new_data --files 46,68,98,140,168,172 \\
        --kinds lying_across,lying_along --start 60 --lateral=-0.15:0.15 --bed-depth 0.25 --out out/lying.json
    python scripts/lying_person_eval.py ... --place rail        # lying across the rail heads

Every other argument is far_range_eval.py's. The results of 23.09 are in
docs/experiments_v0.6.2_margins_lying.json.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import resense.synthetic as syn  # noqa: E402

syn.OBJECT_CATALOGUE["lying_across"] = syn.CatalogueEntry(
    "box", (0.5, 1.8, 0.35), (10, 40), "person lying across the track (0.5 m along, 1.8 m across, 0.35 m tall)")
syn.OBJECT_CATALOGUE["lying_along"] = syn.CatalogueEntry(
    "box", (1.8, 0.5, 0.35), (10, 40), "person lying along the track")


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--bed-depth" in argv:
        k = argv.index("--bed-depth")
        depth = float(argv[k + 1])
        del argv[k:k + 2]
        # far_range_eval looks local_bed_z up in resense.synthetic when it places an object, so the
        # replacement reaches its worker processes (forked after this assignment)
        syn.local_bed_z = lambda xyz, tm, x, lateral, *a, **kw: float(tm.rail_z(x)) - depth
    import far_range_eval
    sys.argv = ["far_range_eval.py"] + argv
    far_range_eval.main()


if __name__ == "__main__":
    main()
