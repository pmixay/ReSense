"""What the CAUTION frames are, how much the trusted gauge range moves, and the frames around the first STOP.

    python caution_stability.py <prefix of the run> <atlas_proposals.json>
"""
import json
import sys
from collections import Counter

import numpy as np

P = [json.loads(line) for line in open(sys.argv[1] + ".jsonl")]
E = [json.loads(line) for line in open(sys.argv[1] + "_extra.jsonl")]
atlas = [a for a in json.load(open(sys.argv[2]))["anchors"] if a["episode"] == "main_approach"]
fr = np.array([a["frame"] for a in atlas])
px = np.array([a["discovery_center"][0] for a in atlas])


def static(w):
    return abs(w["d"] - 105.6) < 3 or abs(w["d"] - 115.1) < 3 or abs(w["d"] - 102.3) < 1.5


cau = [r for r in P if r["decision"] == "CAUTION"]
only_static = [r for r in cau if r["warns"] and all(static(w) for w in r["warns"])]
no_warn = [r for r in cau if not r["warns"]]
print("CAUTION frames %d of %d (%.1f %%)" % (len(cau), len(P), 100 * len(cau) / len(P)))
print("  only the static 102-116 m structure warnings: %d" % len(only_static))
print("  no warning (health-driven): %d; messages %s" % (len(no_warn), Counter(m[:55] for r in no_warn for m in r["msgs"]).most_common(2)))
print("  other warnings (the person etc.): %d" % (len(cau) - len(only_static) - len(no_warn)))
print("first 2000 frames:", dict(Counter(r["decision"] for r in P[:2000])), "| rest:", dict(Counter(r["decision"] for r in P[2000:])))

av = np.array([min(e["axis_valid"] if e["axis_valid"] is not None else np.nan, 250.0) for e in E], dtype=float)
mon = np.array([r["monitored"] if r["monitored"] is not None else np.nan for r in P], dtype=float)
for name, a in (("trusted axis range (axis_valid, capped 250 m)", av), ("reported monitored range", mon)):
    d = np.abs(np.diff(a[~np.isnan(a)]))
    print("%s: median %.0f m, p10-p90 %.0f-%.0f m; frame-to-frame change median %.1f m, p90 %.1f m, >= 20 m in %d of %d (%.1f %%)"
          % (name, np.nanmedian(a), np.nanpercentile(a, 10), np.nanpercentile(a, 90), np.median(d),
             np.percentile(d, 90), (d >= 20).sum(), len(d), 100 * (d >= 20).mean()))

print("\nframe  person_x  axis_valid  monitored  decision  warnings (d, lat, reason)  detections (d, lat, reason)")
for f in list(range(1800, 2700, 150)) + list(range(2700, 3010, 20)):
    r = P[f]
    print(f"{f:5d} {np.interp(f, fr, px):8.1f} {E[f]['axis_valid']!s:>10.10} {r['monitored']!s:>9.9}  {r['decision']:8s} "
          f"{[(w['d'], w['lat'], w['reason']) for w in r['warns']][:3]} {[(d['d'], d['lat'], d['reason']) for d in r['dets']][:2]}")
