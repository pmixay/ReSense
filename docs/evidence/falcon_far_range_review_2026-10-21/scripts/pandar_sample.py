#!/usr/bin/env python3
"""Reviewer's Pandar identity sample: run the gate's own per-recording job (eval_real.run_piece, default config as
the gate loads it) in the checkout RESENSE_REPO on the cached recordings given, writing per-frame JSONL.

    pandar_sample.py --cache DIR --work OUT name [name ...]
"""
import argparse
import os
import sys

REPO = os.environ["RESENSE_REPO"]
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import resense  # noqa: E402
assert os.path.realpath(resense.__file__).startswith(os.path.realpath(REPO)), resense.__file__
import numpy as np  # noqa: E402
import eval_real  # noqa: E402
from scripts.cache_io import cache_files, load_cache_stamps  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--set", action="append", default=[], help="sec.key=val (positive control of the row comparison)")
    ap.add_argument("names", nargs="+")
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    cfg_dict = eval_real.load_cfg_dict(os.path.join(REPO, "configs", "default.yaml"), a.set)
    for name in a.names:
        d = os.path.join(a.cache, name)
        files = cache_files(d)
        stamps = load_cache_stamps(d)
        out = os.path.join(a.work, f"{name}.jsonl")
        eval_real.run_piece((name, list(np.array(files)), cfg_dict, out, stamps, None))
        print(name, len(files), "frames ->", out, flush=True)


if __name__ == "__main__":
    main()
