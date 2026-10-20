#!/usr/bin/env python3
"""Reviewer script: per scene of an approach family, compare reference and candidate per frame.

For each scene: matched frames (ref / cand), the first STOP distance (the first frame of the first run of >= 1
matched frames; the nearer the later = the detection comes later), frames lost (ref matched, cand not), frames
gained (cand matched, ref not).  Used on ``approach_bed`` (objects standing on the bed against a rail, top above
the real head) and ``approach`` families.

    python apb_analyze.py <ref json> <cand json> [<parent json>]
"""
import json
import sys

ref = json.load(open(sys.argv[1]))["results"]
cand = json.load(open(sys.argv[2]))["results"]
par = json.load(open(sys.argv[3]))["results"] if len(sys.argv) > 3 else None
tot_lost = tot_gain = tot_ref = tot_cand = 0
scenes_lost = scenes_later = 0
print("raise side   L    W  delta |  ref cand | first STOP dist ref -> cand | lost frames | gained")
for i, (a, b) in enumerate(zip(ref, cand)):
    s = a["spec"]
    assert {k: v for k, v in s.items() if k != "trace"} == {k: v for k, v in b["spec"].items() if k != "trace"}
    ma = [r["matched"] for r in a["rows"]]
    mb = [r["matched"] for r in b["rows"]]
    da = [r["dist"] for r in a["rows"]]
    fa = next((da[k] for k, m in enumerate(ma) if m), None)
    fb = next((da[k] for k, m in enumerate(mb) if m), None)
    lost = [k for k in range(len(ma)) if ma[k] and not mb[k]]
    gain = [k for k in range(len(ma)) if mb[k] and not ma[k]]
    tot_lost += len(lost)
    tot_gain += len(gain)
    tot_ref += sum(ma)
    tot_cand += sum(mb)
    scenes_lost += bool(lost)
    scenes_later += (fa is not None and (fb is None or fb < fa))
    print(f"{s['raise_']:4.2f} {s['side']:+d} {s['length']:4.1f} {s['width']:4.1f} {s['delta']:+5.2f} | {sum(ma):4d} {sum(mb):4d} |"
          f" {fa} -> {fb} | {lost} | {gain}")
print(f"\nscenes {len(ref)}; scenes with lost frames {scenes_lost}; scenes where the first STOP comes later (nearer) or never "
      f"{scenes_later}; matched frames total ref {tot_ref} cand {tot_cand}; lost {tot_lost} gained {tot_gain}")
