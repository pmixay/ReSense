#!/usr/bin/env python3
"""Reviewer script: are the scenes in which the traced candidate rejected a cluster through the new branch (surface value and a
rejected low cluster in the same frame) exactly the scenes in which the candidate loses STOP frames against the reference?"""
import json
from pathlib import Path

D = Path(__file__).resolve().parent / "out"
ref = json.load(open(D / "synth_approach_bed_apb_ref.json"))["results"]
cand = json.load(open(D / "synth_approach_bed_apb_cand.json"))["results"]
tr = json.load(open(D / "synth_approach_bed_apb_cand_trace.json"))["results"]
lost = {i for i, (a, b) in enumerate(zip(ref, cand)) if any(x["matched"] and not y["matched"] for x, y in zip(a["rows"], b["rows"]))}
branch = {i for i, t in enumerate(tr) if any([v for v in f["surface_calls"] if v is not None] and any(c["rejected"] for c in f["clusters"])
                                             for f in t["trace"])}
print("scenes with lost frames:", len(lost), " scenes with a branch rejection:", len(branch), " identical sets:", lost == branch,
      " only-lost:", sorted(lost - branch), " only-branch:", sorted(branch - lost))
