"""How often each switch is exercised on the gate's recordings (from switch_trace.py's records, default config) and
where the tracker's own verdict depends on it:

* R3: track-frames with a cable_kind (the fast path armed), and track-frames where ``_qualifies`` differs between R3
  on and R3 off (q_r3_on != q_r3_off), with the frame, distance, hits and whether the frame is a STOP row;
* H1: frames with a collision_core cluster, track-frames with core hits, and track-frames where the column hold
  differs with and without the core (hold_core != hold_nocore).

    python trace_stats.py <trace dir> <shipped gate work dir>
"""
import glob
import json
import os
import sys

T, G = sys.argv[1], sys.argv[2]
tot = {"frames": 0, "core_frames": 0, "core_track_frames": 0, "hold_differs": 0, "cable_armed_track_frames": 0,
       "r3_q_differs": 0, "r3_q_differs_on_stop_row": 0}
for f in sorted(glob.glob(os.path.join(T, "*.trace.ndjson"))):
    name = os.path.basename(f)[:-len(".trace.ndjson")]
    gate = [json.loads(x) for x in open(os.path.join(G, name + ".jsonl"))]
    rows = [json.loads(x) for x in open(f)]
    assert len(rows) == len(gate), name
    per = {"core_frames": 0, "core_track_frames": 0, "hold_differs": 0, "cable_armed": 0, "q_differs": []}
    for i, (r, g) in enumerate(zip(rows, gate)):
        tot["frames"] += 1
        per["core_frames"] += bool(r["cores"])
        for t in r["tracks"]:
            per["core_track_frames"] += t["core_hits"] > 0
            per["hold_differs"] += t["hold_core"] != t["hold_nocore"]
            per["cable_armed"] += t["cable_kind"] > 0
            if t["q_r3_on"] != t["q_r3_off"]:
                per["q_differs"].append((i, t["id"], t["last"]["d"], t["hits"], t["cable_kind"], bool(g["obstacle"])))
    tot["core_frames"] += per["core_frames"]
    tot["core_track_frames"] += per["core_track_frames"]
    tot["hold_differs"] += per["hold_differs"]
    tot["cable_armed_track_frames"] += per["cable_armed"]
    tot["r3_q_differs"] += len(per["q_differs"])
    tot["r3_q_differs_on_stop_row"] += sum(q[5] for q in per["q_differs"])
    print(f"{name:40s} frames {len(rows):5d} | H1: core frames {per['core_frames']:4d}, core track-frames "
          f"{per['core_track_frames']:4d}, hold differs {per['hold_differs']:3d} | R3: armed track-frames {per['cable_armed']:4d}, "
          f"q differs {len(per['q_differs'])}")
    for q in per["q_differs"]:
        print(f"      R3 qualifies differ: row {q[0]} track {q[1]} d {q[2]} hits {q[3]} cable_kind {q[4]} STOP row {q[5]}")
print("TOTAL", json.dumps(tot))
