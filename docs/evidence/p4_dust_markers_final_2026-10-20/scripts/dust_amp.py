"""How many returns would the organizer dust need before the final source reacts to it? (information, not a requirement)

For one marked bag: the jury runner's NodeReplica on the frames 0..last dust frame + 1, with K extra returns added,
uniformly inside every dust box of every dust frame (box grown by 0.05 m; the boxes come from the marker file, in the
sensor frame, the same frame as the transform hook receives), K = 0, 10, 30, 100, 300. For each K, with dust.enabled
false and true: the decision at each dust frame, and whether a detection or warning of that frame lies at a dust box
(dust_check.py's tight rule: the box centre within 1.0 m of the detection's footprint). K = 0 is the delivered bag
(its records must equal the plain run's: checked against --ref when given).

    RESENSE_REPO=<checkout> PYTHONPATH=<checkout>:<checkout>/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 \
      python dust_amp.py <bag dir> <markers.jsonl> [--ref <final run.jsonl>] [--ks 0,10,30,100,300] [--seed 11]
"""
import argparse
import json
import os
import sys

import numpy as np

REPO = os.environ["RESENSE_REPO"]
sys.path.insert(0, os.path.join(REPO, "docs/evidence/judgement_2026-10-13/scripts"))
import judge_runner as jr  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("bag")
ap.add_argument("markers")
ap.add_argument("--ref")
ap.add_argument("--ks", default="0,10,30,100,300")
ap.add_argument("--seed", type=int, default=11)
ap.add_argument("--persist", type=int, default=0,
                help="control: instead of the dust frames only, inject the boxes of the first dust frame of each burst "
                     "at the same sensor-frame position into the frames first-N .. first+N (an object that stays)")
a = ap.parse_args()

dust = {}                                          # frame -> [(id, lo, hi)] in the sensor frame
for line in open(a.markers):
    r = json.loads(line)
    for m in r["markers"]:
        if m["type"] == "LINE_LIST" and m["action"] == 0 and m["n_points"]:
            lo, hi = np.array(m["pts_min"]), np.array(m["pts_max"])
            if (hi - lo).max() < 0.1:
                dust.setdefault(r["i"], []).append((m["id"], lo, hi))
if a.persist:
    inj, firsts = {}, [i for i in sorted(dust) if i - 1 not in dust]
    for f0 in firsts:
        for j in range(max(0, f0 - a.persist), f0 + a.persist + 1):
            inj.setdefault(j, []).extend(dust[f0])
else:
    inj, firsts = dict(dust), []
last = max(max(dust), max(inj)) + 1
raws = []
for db3 in jr.db3_files(a.bag):
    for ts, topic, raw in jr.iter_raw(db3):
        raws.append((ts, topic, raw))
        if len(raws) > last:
            break
    break


def tf_for(k):
    def tf(xyz_s, inten, ring, idx):
        if k == 0 or idx not in inj:
            return xyz_s, inten, ring
        rng = np.random.default_rng([a.seed, idx])
        add = [rng.uniform(lo - 0.05, hi + 0.05, size=(k, 3)) for _, lo, hi in inj[idx]]
        pts = np.concatenate(add).astype(xyz_s.dtype)
        n = len(pts)
        return (np.concatenate([xyz_s, pts]), np.concatenate([inten, np.full(n, float(np.median(inten)), dtype=inten.dtype)]),
                None if ring is None else np.concatenate([ring, np.zeros(n, dtype=ring.dtype)]))
    return tf


def run(k, guard):
    rep = jr.NodeReplica(overrides={"dust.enabled": True} if guard else {})
    out = []
    for n, (ts, topic, raw) in enumerate(raws):
        msg, stamp, res, dm, tm = rep.process_raw(raw, topic, n, transform=tf_for(k))
        out.append(jr.record(n, ts / 1e9, stamp, res, dm, tm, msg.header.frame_id, topic))
    return out


def at_box(r, i):
    hits = []
    boxes = inj.get(i, dust.get(i, []))
    for kind, lst in (("det", r["dets"]), ("warn", r["warns"])):
        for d in lst:
            c, sz = d["c"], d["size"]
            for _, lo, hi in boxes:
                f, l = -(lo[1] + hi[1]) / 2, (lo[0] + hi[0]) / 2
                if abs(f - c[0]) <= sz[0] / 2 + 1.0 and abs(l - c[1]) <= sz[1] / 2 + 1.0:
                    hits.append((kind, d["d"], d.get("reason") or ""))
    return hits


ref = [json.loads(line) for line in open(a.ref)][:len(raws)] if a.ref else None
nl = lambda m: [x for x in m if not x.startswith("latency")]
frames = sorted(inj)
print(f"{os.path.basename(a.bag.rstrip('/'))}: frames 0..{last}, dust frames {sorted(dust)}, "
      f"{'persisting object at the boxes of the first frame of each burst, frames ' + str(frames[0]) + '-' + str(frames[-1]) if a.persist else 'K extra returns per dust box in the dust frames only'}")
base = None
for k in [int(v) for v in a.ks.split(",")]:
    for guard in (False, True):
        rows = run(k, guard)
        if k == 0 and not guard:
            base = rows
            if ref is not None:
                tim = {"decode_ms", "detect_ms", "total_ms"}
                bad = sum(any(x[f] != y[f] for f in x if f not in tim and f not in ("msgs", "level")) or nl(x["msgs"]) != nl(y["msgs"])
                          for x, y in zip(rows, ref))
                print(f"  K=0 guard off equals the delivered-bag final run in {len(rows) - bad} of {len(rows)} frames")
        added = sum(rows[i]["n_points"] - base[i]["n_points"] for i in frames) if k and base else 0
        hit_frames = [i for i in frames if at_box(rows[i], i)]
        dec = {}
        for i in frames:
            dec[rows[i]["decision"]] = dec.get(rows[i]["decision"], 0) + 1
        kinds = sorted({h[0] + ("/" + h[2] if h[2] else "") for i in hit_frames for h in at_box(rows[i], i)})
        first_stop = next((i for i in frames if rows[i]["decision"] == "STOP" and at_box(rows[i], i)), None)
        print(f"  K={k:3d} guard {'ON ' if guard else 'off'}: returns added in the {len(frames)} injected frames {added}; decisions there {dec}; "
              f"frames with a detection/warning at a box {len(hit_frames)} {hit_frames[:10]} {kinds}; first STOP at a box: {first_stop}")
