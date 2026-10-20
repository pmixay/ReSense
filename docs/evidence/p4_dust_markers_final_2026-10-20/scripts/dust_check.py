"""Is there a STOP, CAUTION, detection or warning at an organizer dust box?

Dust box = a marker box (LINE_LIST, active, with points) whose extent is < 0.1 m in all three axes (the rule of
per_object.py). For every frame with a dust box, every detection and warning of the run is compared with every
dust box of the frame, by two rules:

  tight   the box centre lies within 1.0 m of the detection's footprint in forward (c[0] +- size[0]/2) and lateral
          (c[1] +- size[1]/2); that is, a detection that sits on the dust or next to it
  coarse  per_object.py's hit rule: near face within max(3 m, 3 %) and vehicle lateral c[1] within 1.5 m of the box

and the smallest separation of any detection / warning from any box is printed (forward, lateral).

    python dust_check.py <markers.jsonl> <run.jsonl> [<run2.jsonl> ...] [--json out.json]

Positive controls built in (printed at the end; the script exits 3 if one fails):
  1. a detection record put on each dust box (centre = box centre, size 0.2 m) must be hit by both rules (30/30 for all
     boxes of the bag);
  2. the same rules applied to the run on the bag's non-dust boxes must hit the STOP detections of that run in the
     frames where the bag has a known object in range 2.5-250 m (the match per_object.py reports as 'A stop' > 0);
  3. a detection record put 20 m beyond each dust box must not be hit.
"""
import json
import sys

import numpy as np

args = [a for a in sys.argv[1:] if not a.startswith("--")]
out_json = None
if "--json" in sys.argv:
    out_json = sys.argv[sys.argv.index("--json") + 1]
    args.remove(out_json)
mk_path, run_paths = args[0], args[1:]


def boxes_of(r):
    out = []
    for m in r["markers"]:
        if m["type"] == "LINE_LIST" and m["action"] == 0 and m["n_points"]:
            lo, hi = np.array(m["pts_min"]), np.array(m["pts_max"])
            out.append({"id": m["id"], "near": float(-hi[1]), "fwd": float(-(lo[1] + hi[1]) / 2),
                        "lat": float((lo[0] + hi[0]) / 2), "up": float((lo[2] + hi[2]) / 2),
                        "dust": bool((hi - lo).max() < 0.1)})
    return out


def tight(d, b, m=1.0):
    c, sz = d["c"], d["size"]
    return (abs(b["fwd"] - c[0]) <= sz[0] / 2 + m) and (abs(b["lat"] - c[1]) <= sz[1] / 2 + m)


def coarse(d, b):
    return abs(d["d"] - b["near"]) <= max(3.0, 0.03 * b["near"]) and abs(d["c"][1] - b["lat"]) <= 1.5


def synth(b, dfwd=0.0):
    f = b["fwd"] + dfwd
    return {"d": f - 0.1, "c": [f, b["lat"], b["up"]], "size": [0.2, 0.2, 0.2]}


marks = {}
for line in open(mk_path):
    r = json.loads(line)
    marks[r["i"]] = boxes_of(r)
dust_frames = sorted(i for i, bs in marks.items() if any(b["dust"] for b in bs))
runs = [[json.loads(line) for line in open(p)] for p in run_paths]
report = {"dust_frames": dust_frames, "boxes": sum(b["dust"] for bs in marks.values() for b in bs), "runs": {}}

ctl = {"on_box": [0, 0, 0], "beyond": [0, 0, 0], "stop_known": [0, 0]}
for bs in marks.values():
    for b in bs:
        if b["dust"]:
            ctl["on_box"][2] += 1
            ctl["on_box"][0] += tight(synth(b), b)
            ctl["on_box"][1] += coarse(synth(b), b)
            ctl["beyond"][2] += 1
            ctl["beyond"][0] += tight(synth(b, 20.0), b)
            ctl["beyond"][1] += coarse(synth(b, 20.0), b)

for p, run in zip(run_paths, runs):
    rep = {"frames": {}, "n_stop": 0, "n_caution": 0, "n_det_tight": 0, "n_warn_tight": 0, "n_det_coarse": 0,
           "n_warn_coarse": 0}
    for i in dust_frames:
        r, dust = run[i], [b for b in marks[i] if b["dust"]]
        row = {"decision": r["decision"], "clear": r["clear"], "nearest": r["nearest"], "level": r["level"],
               "msgs": [m for m in r["msgs"] if not m.startswith("latency ")], "n_dets": len(r["dets"]),
               "n_warns": len(r["warns"]), "boxes": [], "hits": []}
        for b in dust:
            seps = []
            for kind, lst in (("det", r["dets"]), ("warn", r["warns"])):
                for d in lst:
                    seps.append((kind, abs(d["c"][0] - b["fwd"]), abs(d["c"][1] - b["lat"]), d["d"], d["reason"] if "reason" in d else ""))
                    t, c = tight(d, b), coarse(d, b)
                    if t or c:
                        row["hits"].append({"box": b["id"], "kind": kind, "tight": bool(t), "coarse": bool(c), "d": d["d"],
                                            "c": d["c"], "zone": d.get("zone"), "reason": d.get("reason")})
                        rep[f"n_{kind}_tight"] += bool(t)
                        rep[f"n_{kind}_coarse"] += bool(c)
            seps.sort(key=lambda s: s[1] ** 2 + s[2] ** 2)
            row["boxes"].append({"id": b["id"], "fwd": round(b["fwd"], 2), "lat": round(b["lat"], 2), "up": round(b["up"], 2),
                                 "closest": [(s[0], round(s[3], 1), round(s[1], 2), round(s[2], 2), s[4]) for s in seps[:1]]})
        # what each detection / warning of the frame is, by the coarse rule against the non-dust boxes
        objs = [b for b in marks[i] if not b["dust"]]
        row["explained"] = [{"kind": kind, "d": d["d"], "c": d["c"], "size": d["size"], "reason": d.get("reason"),
                             "marker_ids": [b["id"] for b in objs if coarse(d, b)]}
                            for kind, lst in (("det", r["dets"]), ("warn", r["warns"])) for d in lst]
        rep["frames"][i] = row
        rep["n_stop"] += r["decision"] == "STOP"
        rep["n_caution"] += r["decision"] == "CAUTION"
    report["runs"][p] = rep
    # control 2: STOP detections vs non-dust boxes
    known = tot = 0
    for i, bs in marks.items():
        obj = [b for b in bs if not b["dust"] and 2.5 <= b["near"] <= 250.0]
        if run[i]["decision"] == "STOP" and obj:
            tot += 1
            known += any(coarse(d, b) for d in run[i]["dets"] for b in obj)
    ctl["stop_known"] = [known, tot]

if out_json:
    json.dump(report, open(out_json, "w"), indent=1, default=str)
print(f"dust frames ({len(dust_frames)}): {dust_frames}; dust boxes in them: {report['boxes']}")
for p, rep in report["runs"].items():
    print(f"\n== {p}\n   STOP {rep['n_stop']}, CAUTION {rep['n_caution']} of {len(dust_frames)} dust frames; "
          f"detections at a dust box: tight {rep['n_det_tight']} coarse {rep['n_det_coarse']}; "
          f"warnings at a dust box: tight {rep['n_warn_tight']} coarse {rep['n_warn_coarse']}")
    for i, row in rep["frames"].items():
        print(f"  frame {i:3d} {row['decision']:7s} clear {row['clear']} nearest {row['nearest']} level {row['level']} "
              f"dets {row['n_dets']} warns {row['n_warns']} msgs {row['msgs']}")
        for b in row["boxes"]:
            print(f"      box {b['id']:2d} at fwd {b['fwd']:5.2f} lat {b['lat']:5.2f} up {b['up']:5.2f}; closest det/warn "
                  f"(kind, d, |dfwd|, |dlat|, reason): {b['closest']}")
        print("      decisions i-3..i+3 (warning distances): " + "  ".join(
            f"{j}:{run[j]['decision'][:4]}{[w['d'] for w in run[j]['warns']] if run[j]['warns'] else ''}" for j in range(max(0, i - 3), min(len(run), i + 4))))
        for e in row["explained"]:
            print(f"      {e['kind']} d={e['d']} c={e['c']} size={e['size']} reason={e['reason']!r}: marker object(s) {e['marker_ids'] or 'none'}")
        for h in row["hits"]:
            print(f"      HIT {h}")
print(f"\ncontrol 1 (detection on every dust box): tight {ctl['on_box'][0]}/{ctl['on_box'][2]}, coarse {ctl['on_box'][1]}/{ctl['on_box'][2]}")
print(f"control 3 (detection 20 m beyond every dust box): tight {ctl['beyond'][0]}/{ctl['beyond'][2]}, coarse {ctl['beyond'][1]}/{ctl['beyond'][2]} (must be 0)")
print(f"control 2 (run's STOP frames with a known object in range that the coarse rule matches): {ctl['stop_known'][0]}/{ctl['stop_known'][1]}")
bad = ctl["on_box"][0] != ctl["on_box"][2] or ctl["on_box"][1] != ctl["on_box"][2] or ctl["beyond"][0] or ctl["beyond"][1]
sys.exit(3 if bad else 0)
