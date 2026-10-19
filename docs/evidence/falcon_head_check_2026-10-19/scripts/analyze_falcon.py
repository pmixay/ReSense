"""Analyse the HEAD run on the Falcon recording (outputs of falcon_dual_stream.py)."""
import json
import sys
from collections import Counter

import numpy as np

OUT = sys.argv[1]                       # prefix of the run: <prefix>.jsonl, _ros.jsonl, _extra.jsonl
ATLAS = sys.argv[2]                     # atlas_proposals.json (independent raw review; never used as detector input)


def load(p):
    return [json.loads(line) for line in open(p)]


prim, ros, extra = load(OUT + ".jsonl"), load(OUT + "_ros.jsonl"), load(OUT + "_extra.jsonl")
print("frames: primary %d, explicit-ROS %d, extra %d" % (len(prim), len(ros), len(extra)))

# ---- A. decisions
for name, rows in (("default launch (Pandar axes + auto_calibrate)", prim), ("explicit falcon_ros axes", ros)):
    c = Counter(r["decision"] for r in rows)
    print("\n== %s: %s" % (name, dict(c)))
    first = {d: next((r["i"] for r in rows if r["decision"] == d), None) for d in ("GO", "CAUTION", "STOP")}
    print("   first frame of each decision:", first)

# ---- B. calibration state over time
print("\n== calibration (mount) of the primary (default launch)")
for k in (0, 1, 2, 3, 5, 10, 50, 100, 200, 400, 1000, 2000, 3000, 4000, len(prim) - 1):
    m = extra[k]["mount_full"] or {}
    print("   frame %4d: decision %-7s status=%-9s orient=%s roll=%s pitch=%s height=%s lateral=%s used=%s conflict=%s" % (
        k, prim[k]["decision"], m.get("status"), m.get("orientation") or m.get("axes"), m.get("roll_deg", m.get("roll")),
        m.get("pitch_deg", m.get("pitch")), m.get("height"), m.get("lateral"), m.get("frames_used"), m.get("orientation_conflict")))
print("   keys of mount dict:", sorted((extra[0]["mount_full"] or {}).keys()))
st = Counter((extra[i]["mount_full"] or {}).get("status") for i in range(len(extra)))
print("   mount status over all frames:", dict(st))
st2 = Counter((r.get("mount_full") or {}).get("status") for r in ros)
print("   explicit ROS mount status over all frames:", dict(st2))

# ---- C. person: reviewed raw trajectory vs detector output
atlas = json.load(open(ATLAS))["anchors"]
main = [a for a in atlas if a["episode"] == "main_approach"]
fr = np.array([a["frame"] for a in main])
px = np.array([a["discovery_center"][0] for a in main])
py = np.array([a["discovery_center"][1] for a in main])
npts = np.array([a["raw_crop_points"] for a in main])


def person_at(f):
    if f < fr[0] or f > fr[-1]:
        return None
    return float(np.interp(f, fr, px)), float(np.interp(f, fr, py))


def analyse(rows, name, tol_abs=4.0):
    print("\n== person association, %s (distance match |d - person_x| <= max(%.0f m, 3 %%)" % (name, tol_abs))
    first_stop = first_warn = None
    n_stop_matched = n_frames = 0
    series = []
    for r in rows:
        p = person_at(r["i"])
        if p is None:
            continue
        n_frames += 1
        x = p[0]
        tol = max(tol_abs, 0.03 * x)
        sm = [d for d in r["dets"] if abs(d["d"] - x) <= tol]
        wm = [d for d in r["warns"] if abs(d["d"] - x) <= tol]
        if sm and r["decision"] == "STOP":
            n_stop_matched += 1
            if first_stop is None:
                first_stop = (r["i"], x, sm[0]["d"], sm[0]["lat"])
        if wm and first_warn is None:
            first_warn = (r["i"], x, wm[0]["d"], wm[0]["lat"])
        series.append((r["i"], x, bool(sm and r["decision"] == "STOP")))
    print("   frames inside reviewed trajectory: %d; STOP frames matched to the person: %d" % (n_frames, n_stop_matched))
    print("   first matched warning (frame, person range, det d, det lat):", first_warn)
    print("   first matched STOP    (frame, person range, det d, det lat):", first_stop)
    if first_stop:
        f0 = first_stop[0]
        after = [s for s in series if s[0] >= f0]
        print("   from the first matched STOP to the end of the trajectory: %d/%d frames matched STOP (%.1f %%)" % (
            sum(s[2] for s in after), len(after), 100 * sum(s[2] for s in after) / len(after)))
        # stability by range band (person range at that frame)
        for lo, hi in ((150, 130), (130, 100), (100, 60), (60, 20), (20, 0)):
            band = [s for s in series if hi <= s[1] < lo and s[0] >= f0]
            if band:
                print("     person range %3d-%3d m: %3d/%3d frames STOP matched" % (hi, lo, sum(s[2] for s in band), len(band)))
    # bands ahead of the first STOP: frames where the person is farther than the first-STOP range
    far = [s for s in series if first_stop and s[1] > first_stop[1] + 0.5]
    print("   frames with the person farther than the first-STOP range: %d (none of them matched as STOP by definition)" % len(far))
    return first_stop, first_warn


analyse(prim, "default launch")
analyse(ros, "explicit ROS")

# reviewed raw returns on the person vs range
print("\n== reviewed raw returns inside the person crop (anchor file) by range")
for lo, hi in ((240, 260), (200, 240), (150, 200), (120, 150), (90, 120), (50, 90), (20, 50), (0, 20)):
    m = (px >= lo) & (px < hi)
    if m.any():
        print("   %3d-%3d m: median %5.0f returns (n=%d anchors)" % (lo, hi, np.median(npts[m]), m.sum()))

# ---- D. range statistics
print("\n== uncropped raw returns")
g250 = np.array([e["n_gt250"] for e in extra])
g300 = np.array([e["n_gt300"] for e in extra])
rmax = np.array([e["rmax"] or 0 for e in extra])
nraw = np.array([e["n_raw"] for e in extra])
print("   raw points per frame: median %d (min %d, max %d)" % (np.median(nraw), nraw.min(), nraw.max()))
print("   returns > 250 m per frame: median %.0f, max %d; frames with any: %d/%d" % (np.median(g250), g250.max(), (g250 > 0).sum(), len(g250)))
print("   returns > 300 m per frame: median %.0f, max %d; frames with >=10: %d/%d" % (np.median(g300), g300.max(), (g300 >= 10).sum(), len(g300)))
print("   per-frame max range: median %.0f m, p95 %.0f m, max %.0f m" % (np.median(rmax), np.percentile(rmax, 95), rmax.max()))
H = np.array([e["range_hist10"] for e in extra])
tot = H.sum(axis=0)
edges = np.arange(0, 610, 10)
print("   returns per 10 m bin summed over all frames (millions): ", end="")
for lo in (0, 50, 100, 150, 200, 250, 300, 350, 400, 500):
    print("%d-%d m: %.2fM  " % (lo, lo + 50, tot[lo // 10:(lo + 50) // 10].sum() / 1e6), end="")
print()

# ---- E. trusted axis and monitored range the node would report
print("\n== trusted axis / monitored range (default launch)")
av = np.array([(e["axis_valid"] if e["axis_valid"] is not None else np.nan) for e in extra], dtype=float)
mon = np.array([(r["monitored"] if r["monitored"] is not None else np.nan) for r in prim], dtype=float)
cl = np.array([r["clear"] for r in prim], dtype=float)
print("   axis_valid: median %.0f m, p10 %.0f, p90 %.0f, max %.0f; frames >= 250: %d" % (np.nanmedian(av), np.nanpercentile(av, 10), np.nanpercentile(av, 90), np.nanmax(av), np.nansum(av >= 250)))
print("   monitored : median %.0f m, p10 %.0f, p90 %.0f, max %.0f; frames >= 250: %d" % (np.nanmedian(mon), np.nanpercentile(mon, 10), np.nanpercentile(mon, 90), np.nanmax(mon), np.nansum(mon >= 250)))
print("   clear_distance (legacy policy in this replica): median %.0f m, max %.0f m" % (np.median(cl), cl.max()))
# static support alarms
print("\n== frames with a STOP detection NOT matched to the person (default launch)")
oth = []
for r in prim:
    if r["decision"] != "STOP":
        continue
    p = person_at(r["i"])
    ok = False
    if p is not None:
        x = p[0]
        ok = any(abs(d["d"] - x) <= max(4.0, 0.03 * x) for d in r["dets"])
    if not ok:
        oth.append(r)
print("   %d STOP frames unmatched; their detection distances (m) by 10-m band:" % len(oth))
c = Counter(int(min(d["d"] for d in r["dets"]) // 10 * 10) for r in oth if r["dets"])
print("   ", dict(sorted(c.items())))
