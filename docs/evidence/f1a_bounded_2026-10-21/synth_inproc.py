#!/usr/bin/env python3
"""Run a synthetic family in ONE process (no Pool), so trace_count.py's counters see every call:
    python synth_inproc.py <review|ext> <family> <out.json>"""
import json, os, sys
from pathlib import Path
kind, family, out = sys.argv[1:4]
sys.path.insert(0, "/home/user/ReSense/docs/evidence/f1a_completion_review_2026-10-20" if kind == "review"
                else "/home/user/ReSense/docs/evidence/f1a_bounded_2026-10-21")
mod = __import__("synth_controls" if kind == "review" else "ext_scenes")
specs = mod.scenes(family, False) if kind == "review" else mod.scenes(family)
res = [mod.run_scene(s) for s in specs]
Path(out).write_text(json.dumps(dict(repo=os.environ["RESENSE_REPO"], family=family, results=res)) + "\n")
print(family, len(res), "scenes", sum(r["matched_frames"] for r in res), "matched")
