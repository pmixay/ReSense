"""N5 label supplement from the organizers' markers (synth_markers_2026-10-19, "What it changes"): the rows of the
object N5 missed (synthetic_tunnels, marker id 18) and the list of N5 rows that match no marker object. The N5 files
of 17.10 are not changed; a consumer adds the rows and drops or flags the listed ones.

Rows of the missed object: one per frame with the box's near face at 2.5-250 m, in N5's frame and schema
(sensor_axis_mapped: forward = -sensor_y, left = sensor_x, up = sensor_z; distance = near face, lateral = box centre),
from the marker box itself (no raw points: n_points is None).

    python n5_supplement.py <markers_tunnels.jsonl> <synth_markers out dir> <out.json>
"""
import json
import sys

markers, out_dir, out = sys.argv[1], sys.argv[2], sys.argv[3]
MISSED_ID, NAME = 18, "box_left_0"
rows = {}
for line in open(markers):
    r = json.loads(line)
    for m in r["markers"]:
        if m["id"] != MISSED_ID or m["type"] != "LINE_LIST" or m["action"] != 0 or not m["n_points"]:
            continue
        lo, hi = m["pts_min"], m["pts_max"]
        fwd0, fwd1 = -hi[1], -lo[1]
        if not 2.5 <= fwd0 <= 250.0:
            continue
        lat = (lo[0] + hi[0]) / 2
        rows[f"{r['i']:05d}"] = [{
            "name": NAME, "label": NAME, "kind": "box", "distance": round(fwd0, 3), "lateral": round(lat, 5),
            "lateral_sensor": round(lat, 5),
            "bbox": [[round(fwd0, 3), round(lo[0], 5), round(lo[2], 5)], [round(fwd1, 3), round(hi[0], 5), round(hi[2], 5)]],
            "size": [round(fwd1 - fwd0, 3), round(hi[0] - lo[0], 3), round(hi[2] - lo[2], 3)],
            "n_points": None, "n_unique_points": None, "gauge_relation": "unknown", "in_gauge": None,
            "annotation_confidence": "organizer_marker",
            "source": "organizers' marker box (synth_markers_2026-10-19, marker id 18), not raw-point geometry",
            "coordinate_frame": "sensor_axis_mapped"}]
unmatched = []
for bag in ("platform", "switch", "tunnels"):
    cmp = json.load(open(f"{out_dir}/{bag}_vs_n5.json"))
    for name, t in cmp["n5_tracks"].items():
        for u in t["unmatched"]:
            unmatched.append({"bag": f"synthetic_{bag}", "frame": u["frame"], "name": name, "n5_distance": u["n5_distance"],
                              "n5_lateral": u["n5_lateral"], "n5_points": u["n5_points"],
                              "nearest_marker": u["nearest_marker"]})
res = {"_meta": {
    "schema": "resense-n5-marker-supplement-v1",
    "basis": "organizers' marker boxes, docs/evidence/synth_markers_2026-10-19; N5 labels of 17.10 unchanged",
    "add": {"bag": "synthetic_tunnels", "object": NAME, "marker_id": MISSED_ID, "obstacles_md_item": "tunnels 1, small cube left",
            "frames": len(rows), "first_frame": min(map(int, rows)), "last_frame": max(map(int, rows)),
            "gauge_relation": "unknown",
            "gauge_note": "inner face 1.31-1.33 m left of the sensor axis at 1-5 m (frames 58-60); the replayed 1.1.0 run has "
                          "no detection or warning on it in any frame, so probably outside the 2.1 m gauge; not checked "
                          "against the rails"},
    "flag": {"rows": len(unmatched), "status": "matches no marker object (sparse 1-4 point rows); drop when scoring "
             "against the markers, keep when scoring against N5 as of 17.10"}},
    "rows": rows, "unmatched_n5_rows": unmatched}
json.dump(res, open(out, "w"), indent=1)
print(f"added {len(rows)} rows of {NAME} (frames {res['_meta']['add']['first_frame']}-{res['_meta']['add']['last_frame']}); "
      f"flagged {len(unmatched)} N5 rows: " + ", ".join(f"{u['bag'][10:]} {u['frame']}" for u in unmatched))
