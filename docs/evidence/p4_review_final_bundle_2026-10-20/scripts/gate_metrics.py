"""Rebuild the gate JSON from the raw rows and compare the 208 non-timing metrics.

    python gate_metrics.py <extracted raw-replay dir> <evidence dir of the published gate JSONs> [<P4 gate JSON>]

Needs the repository (scripts/regression_gate.py, resense.metrics, the labels) importable: run from the checkout with
PYTHONPATH set to it. The recordings / five_empty / ride / set_O sections of ``gate-a-<side>.json`` are rebuilt from
``gate-a-<side>/*.jsonl`` with the gate's own scorer, set F from ``setF_straight.json``; own counters (frames, STOP frames,
advisory frames, STOP episodes) are recomputed with no repository code. ``metrics()`` lists the gated and informational
keys; the 16 latency keys are the only ones excluded from "non-timing".
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
import scripts.eval_real as er
import scripts.regression_gate as rg

raw, ev = sys.argv[1], sys.argv[2]
p4 = sys.argv[3] if len(sys.argv) > 3 else None


def canon(x):
    return json.loads(json.dumps(x))


def rebuild(side):
    d = f"{raw}/gate-a-{side}"
    pub = json.load(open(f"{ev}/gate-a-{side}.json"))
    cfg = er.load_cfg(f"{d}/config.yaml", [])
    lab = lambda n: os.path.join(os.getcwd(), er.LABELS[n]) if n in er.LABELS else None
    rec = {b: rg.recording_entry(b, [f"{d}/{b}.jsonl"], cfg, lab(b)) for b in rg.SIX}
    five = {k: sum(rec[b][k] for b in rg.FIVE_EMPTY) for k in ("frames", "alarm_frames", "alarm_events", "stop_episodes", "advisory_frames")}
    so = rg.set_o_entry([f"{d}/{rg.SET_O}.jsonl"], os.path.join(os.getcwd(), rg.SET_O_LABELS))
    r = rg.recording_entry(rg.RIDE, [f"{d}/new_data_{k}.jsonl" for k in range(8)], cfg)
    ride = {"available": True, "chunks": 8, **{k: v for k, v in r.items() if k not in ("labelled", "first_alarm_frame")}}
    setf = rg.set_f_entry(json.load(open(f"{d}/setF_straight.json")))
    mine = {"recordings": rec, "five_empty": five, "ride": ride, "set_O": so, "set_F_straight": setf}
    bad = [k for k, v in mine.items() if canon(v) != pub[k]]
    print(f"{side}: sections rebuilt from raw rows {list(mine)}; differing from the published gate JSON: {bad or 'none'}")
    # own counters, no repository code
    for n in list(rg.SIX) + [rg.SET_O]:
        rows = [json.loads(line) for line in open(f"{d}/{n}.jsonl")]
        st = sum(bool(x["obstacle"]) for x in rows)
        adv = sum(bool(x["warning"]) for x in rows)
        ep = sum(1 for i, x in enumerate(rows) if x["obstacle"] and (i == 0 or not rows[i - 1]["obstacle"]))
        p = pub["recordings"].get(n)
        ok = len(rows) == (p or pub["set_O"])["frames"] and st == (p or pub["set_O"])["alarm_frames"]
        if p:
            ok = ok and adv == p["advisory_frames"] and ep == p["stop_episodes"]
        print(f"   own count {n:42s} frames {len(rows):5d} STOP {st:4d} advisory {adv:4d} episodes {ep:3d} {'OK' if ok else 'MISMATCH'}")
    ep = fr = st = 0
    for k in range(8):
        prev = False
        for line in open(f"{d}/new_data_{k}.jsonl"):
            o = bool(json.loads(line)["obstacle"])
            fr += 1
            st += o
            ep += o and not prev
            prev = o
    print(f"   own ride: frames {fr} STOP frames {st} STOP episodes {ep} | published {pub['ride']['frames']} {pub['ride']['alarm_frames']} {pub['ride']['stop_episodes']}")
    return pub


cand, ref = rebuild("candidate"), rebuild("reference")
mc, mr = rg.metrics(cand), rg.metrics(ref)
nt = [k for k in mc if not k.startswith("latency_ms")]
print(f"metric keys {len(mc)} (same keys on both sides: {set(mc) == set(mr)}); non-timing {len(nt)}; gated {sum(mc[k][2] for k in nt)}")
print(f"non-timing metrics equal, candidate vs reference: {sum(mc[k][0] == mr[k][0] for k in nt)} of {len(nt)}")
print(f"code: candidate {cand['code']['commit'][:7]} reference {ref['code']['commit'][:7]}; gate passed {cand['gate']['passed']}/{ref['gate']['passed']}, "
      f"allow {cand['gate']['allow']}, better {len(cand['gate']['better'])}, worse {len(cand['gate']['worse_gated'])}")
if p4:
    mp = rg.metrics(json.load(open(p4)))
    d = [k for k in nt if mc[k][0] != mp[k][0]]
    print(f"P4's own gate run on f56ad5e ({os.path.basename(p4)}): non-timing metrics differing from the candidate: {len(d)} {d[:5]}")
