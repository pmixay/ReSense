#!/usr/bin/env python3
"""Development check of the mechanism (not a measurement): run_piece on the first N frames of a gate cache with
several --set lists; writes <out>/<tag>.jsonl.   devrun.py <tree> <bag> <N> <outdir> tag:k=v,k=v ..."""
import os, sys
T, bag, N, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
os.chdir(T); sys.path.insert(0, T)
from scripts import eval_real
from scripts.cache_io import cache_files, load_cache_stamps
d = os.path.join("/data/cache", bag)
files = cache_files(d)[:N]
stamps = load_cache_stamps(d)
os.makedirs(out, exist_ok=True)
for spec in sys.argv[5:]:
    tag, _, sets = spec.partition(":")
    sets = [s for s in sets.split(",") if s]
    cfg = eval_real.load_cfg_dict(os.path.join(T, "configs/default.yaml"), sets)
    eval_real.run_piece((bag, list(files), cfg, os.path.join(out, f"{tag}.jsonl"), stamps, None))
    print("done", tag, flush=True)
