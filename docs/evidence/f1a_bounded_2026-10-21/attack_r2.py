#!/usr/bin/env python3
"""PROTOCOL revision 2, row R2: the review's attack families with the measured per-ring azimuth phases forced on
every scene and a chosen noise seed. Wrapper only: imports the review's attack.py (unchanged, path in REVIEW_DIR)
and sets ``az_off = {"mode": "measured"}`` where a scene has none (the Falcon raster keeps its own rays) and
``seed_off``; everything else is the review's code.

    RESENSE_REPO=<checkout> REVIEW_DIR=<review evidence dir> python attack_r2.py --family F --seed S --out o.json
"""
import argparse, json, os, sys
from multiprocessing import Pool
from pathlib import Path
sys.path.insert(0, os.environ["REVIEW_DIR"])
import attack  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--family", required=True)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--out", required=True)
ap.add_argument("--jobs", type=int, default=4)
a = ap.parse_args()
import resense
assert Path(resense.__file__).resolve().is_relative_to(Path(os.environ["RESENSE_REPO"]).resolve())
specs = attack.scenes(a.family)
for s in specs:
    if s.get("rays") != "falcon" and s.get("az_off") is None:
        s["az_off"] = {"mode": "measured"}
    s["seed_off"] = s.get("seed_off", 0) + a.seed
    s["trace"] = False
with Pool(a.jobs) as pool:
    res = list(pool.imap(attack.run_scene, specs))
Path(a.out).write_text(json.dumps(dict(repo=os.environ["RESENSE_REPO"], family=a.family, seed=a.seed, results=res)) + "\n")
print(a.family, a.seed, len(res), "scenes", sum(r["matched_frames"] for r in res), "matched")
