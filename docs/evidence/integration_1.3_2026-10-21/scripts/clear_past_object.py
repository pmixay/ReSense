#!/usr/bin/env python3
"""Set O: frames where clear_distance extends past a labelled object inside the gauge (docs/ARCHITECTURE.md /
docs/ALGORITHM.md "300 of 605 frames, 68 of them GO", clear-distance review F2), per definition variant.
Object inside = a plausible label row with n_in_envelope > 0 (points in the strict envelope); its distance = the
label's near face X (bbox[0][0]); the frame's object = the nearest such object. Past = clear > that X + tol.
Decision: obstacle -> STOP, warning -> CAUTION, else GO.
    clear_past_object.py <labels/cloud_with_fake_obj.json> <rows.jsonl> [...]"""
import json, sys
lab = json.load(open(sys.argv[1]))
for p in sys.argv[2:]:
    rows = [json.loads(l) for l in open(p)]
    assert len(rows) == lab["_meta"]["frames"] == 1510
    for name, sel in (("n_in_envelope>0", lambda o: o["plausible"] and o["n_in_envelope"] > 0),
                      ("in_gauge intent & plausible", lambda o: o["plausible"] and o["in_gauge"]),
                      ("in_gauge intent & plausible & n_in_envelope>0", lambda o: o["plausible"] and o["in_gauge"] and o["n_in_envelope"] > 0)):
        for tol in (0.0, 1.0):
            n = past = go = 0; dec = {"GO": 0, "CAUTION": 0, "STOP": 0}
            for i, r in enumerate(rows):
                objs = [o for o in lab.get(f"{i:05d}", []) if sel(o)]
                if not objs:
                    continue
                n += 1
                x = min(o["bbox"][0][0] for o in objs)
                c = r["clear_distance"]
                d = "STOP" if r["obstacle"] else "CAUTION" if r["warning"] else "GO"
                if c is not None and c > x + tol:
                    past += 1; dec[d] += 1
            print(f"{p.split('/')[-2]:5s} {name:48s} tol {tol}: frames {n}, clear past the object {past} {dec}")
