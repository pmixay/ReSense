"""Summarise the organizers' marker boxes: per marker id, then per object (boxes that move together).

Input: <prefix>.jsonl from read_markers.py. Active markers are LINE_LIST with action ADD (0); their points are the
box wireframe in the sensor frame (hesai_lidar). The Pandar recordings map sensor -y -> forward, +x -> left, +z -> up
(configs/default.yaml).

1. Segments: the boxes of one marker id, split where the id would be reused for another object: the box height changes
   by more than --max-size-change m (not the horizontal extents: the boxes are axis-aligned in the sensor frame, so
   a box that turns with the track changes them, a 2 m cube between 2.0 and 2.6 m), or the box moves more than --max-jump m per frame elapsed (the
   train covers <= 1.6 m per frame, the marker positions step unevenly, up to ~3 m in one frame). Far objects are
   marked only in the frames where they have returns, so one object can be absent for 80 frames.
2. Objects: segments joined when they are present in the same frames (>= half of the shorter one) with centres
   within 0.5 m forward and 1.5 m lateral (median over the shared frames): the person is several part boxes.
   Per frame an object is the union of its boxes.
3. Speed: the train's speed from the forward distance of the longest object and the bag time, while it approaches.

Writes <prefix>_objects.json and prints one line per segment and per object, in order of first appearance.

    python marker_objects.py <prefix> [--max-size-change 0.15] [--max-jump 10]
"""
import argparse
import json

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("prefix")
ap.add_argument("--max-size-change", type=float, default=0.15)
ap.add_argument("--max-jump", type=float, default=10.0)
a = ap.parse_args()

rows = [json.loads(line) for line in open(a.prefix + ".jsonl")]
bag_t = {r["i"]: r["bag_t"] for r in rows}
per_id = {}
for r in rows:
    for m in r["markers"]:
        if m["type"] != "LINE_LIST" or m["action"] != 0 or not m["n_points"]:
            continue
        lo, hi = np.array(m["pts_min"]), np.array(m["pts_max"])
        # forward = -y, lateral = x, up = z: box as (fwd_lo, fwd_hi, lat_lo, lat_hi, up_lo, up_hi)
        box = (-hi[1], -lo[1], lo[0], hi[0], lo[2], hi[2])
        per_id.setdefault(m["id"], []).append((r["i"], box, m["color"]))

segments = []
for mid, entries in per_id.items():
    cur = []
    for e in entries:
        if cur:
            pf, pb, _ = cur[-1]
            c0 = ((pb[0] + pb[1]) / 2, (pb[2] + pb[3]) / 2)
            c1 = ((e[1][0] + e[1][1]) / 2, (e[1][2] + e[1][3]) / 2)
            ds = abs((e[1][5] - e[1][4]) - (pb[5] - pb[4]))
            if ds > a.max_size_change or np.hypot(c1[0] - c0[0], c1[1] - c0[1]) > a.max_jump * (e[0] - pf):
                segments.append((mid, cur))
                cur = []
        cur.append(e)
    segments.append((mid, cur))


def centre(b):
    return (b[0] + b[1]) / 2, (b[2] + b[3]) / 2


seg_info = []
for n, (mid, ent) in enumerate(segments):
    fr = {f: b for f, b, _ in ent}
    seg_info.append({"seg": n, "id": mid, "frames": fr, "color": ent[0][2]})

parent = list(range(len(seg_info)))


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


for i in range(len(seg_info)):
    for j in range(i + 1, len(seg_info)):
        fi, fj = seg_info[i]["frames"], seg_info[j]["frames"]
        common = sorted(set(fi) & set(fj))
        if len(common) < 0.5 * min(len(fi), len(fj)):
            continue
        df = np.median([abs(centre(fi[f])[0] - centre(fj[f])[0]) for f in common])
        dl = np.median([abs(centre(fi[f])[1] - centre(fj[f])[1]) for f in common])
        if df <= 0.5 and dl <= 1.5:
            parent[find(i)] = find(j)

groups = {}
for i in range(len(seg_info)):
    groups.setdefault(find(i), []).append(seg_info[i])

objects = []
for segs in groups.values():
    frames = sorted({f for s in segs for f in s["frames"]})
    union = []
    for f in frames:
        bs = np.array([s["frames"][f] for s in segs if f in s["frames"]])
        union.append((f, bs[:, 0].min(), bs[:, 1].max(), bs[:, 2].min(), bs[:, 3].max(), bs[:, 4].min(), bs[:, 5].max()))
    u = np.array(union)
    size = np.stack([u[:, 2] - u[:, 1], u[:, 4] - u[:, 3], u[:, 6] - u[:, 5]], 1)
    lat_c = (u[:, 3] + u[:, 4]) / 2
    f = u[:, 0].astype(int)
    objects.append({
        "ids": sorted({s["id"] for s in segs}), "n_boxes": len(segs),
        "first": int(f[0]), "last": int(f[-1]), "n_frames": int(len(f)), "gaps": int((np.diff(f) > 1).sum()),
        "fwd_first": round(float(u[0, 1]), 2), "fwd_last": round(float(u[-1, 1]), 2), "fwd_min": round(float(u[:, 1].min()), 2),
        "lat_centre_first_last": [round(float(lat_c[0]), 2), round(float(lat_c[-1]), 2)],
        "lat_extent": [round(float(u[:, 3].min()), 2), round(float(u[:, 4].max()), 2)],
        "up_extent": [round(float(u[:, 5].min()), 2), round(float(u[:, 6].max()), 2)],
        "size_median_fwd_lat_up": [round(float(v), 2) for v in np.median(size, 0)],
        "size_max": [round(float(v), 2) for v in size.max(0)],
        "color": segs[0]["color"],
        "track": [[int(r[0]), round(float(r[1]), 2), round(float((r[3] + r[4]) / 2), 2)] for r in union],
    })
objects.sort(key=lambda o: (o["first"], o["fwd_first"]))

for s in sorted(seg_info, key=lambda s: min(s["frames"])):
    fr = sorted(s["frames"])
    print(f"segment id {s['id']:2d}: frames {fr[0]:4d}-{fr[-1]:4d} ({len(fr)})  fwd {centre(s['frames'][fr[0]])[0]:7.1f} -> "
          f"{centre(s['frames'][fr[-1]])[0]:7.1f}")
print()
for k, o in enumerate(objects, 1):
    print(f"object {k:2d} ids {o['ids']}: frames {o['first']:4d}-{o['last']:4d} ({o['n_frames']}, gaps {o['gaps']}) "
          f"near face {o['fwd_first']:7.1f} -> {o['fwd_last']:6.1f} m (min {o['fwd_min']:.1f}); lateral centre "
          f"{o['lat_centre_first_last']} extent {o['lat_extent']}; up {o['up_extent']}; size f,l,u {o['size_median_fwd_lat_up']} "
          f"(max {o['size_max']})")

# train speed from the longest object while its distance shrinks (forward differences over 10 frames)
lo = max(objects, key=lambda o: o["n_frames"])
tr = np.array([[bag_t[f], d] for f, d, _ in lo["track"]])
sp = -(tr[10:, 1] - tr[:-10, 1]) / (tr[10:, 0] - tr[:-10, 0])
speed = {"from_object_ids": lo["ids"], "max_mps": round(float(sp.max()), 2), "first_mps": round(float(sp[0]), 2),
         "last_mps": round(float(sp[-1]), 2)}
print(f"\nspeed from object {lo['ids']}: first {speed['first_mps']} m/s, max {speed['max_mps']} m/s, last {speed['last_mps']} m/s")
active = [sum(1 for m in r["markers"] if m["type"] == "LINE_LIST" and m["action"] == 0) for r in rows]
summary = {"messages": len(rows), "markers_per_message": sorted({len(r["markers"]) for r in rows}),
           "active_boxes_per_message": [min(active), max(active)], "messages_without_boxes": active.count(0),
           "segments": len(seg_info), "objects": objects, "speed": speed}
print(f"messages {len(rows)}; active boxes per message: min {min(active)}, max {max(active)}; without any: {active.count(0)}")
json.dump(summary, open(a.prefix + "_objects.json", "w"))
