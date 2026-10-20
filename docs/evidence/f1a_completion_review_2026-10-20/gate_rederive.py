#!/usr/bin/env python3
"""Reviewer script (own; does not use the author's compare_*.py / audit.py): re-derive the headline numbers from the two
stored gate reports by a generic leaf-by-leaf diff of the whole JSON.

* every leaf path that differs between reference and candidate (timing / provenance subtrees listed separately),
* the claimed numbers read straight from the leaves,
* positive controls: (a) swapping the two reports flips the sign of every numeric difference; (b) a copy of the
  candidate with one number changed (ride alarm_frames 102 -> 103) is detected as one more differing leaf.

    python gate_rederive.py <gate-c-reference.json> <gate-c-candidate.json>
"""
import copy
import json
import sys

ref = json.load(open(sys.argv[1]))
cand = json.load(open(sys.argv[2]))
TIMING = ("latency_ms", "created", "run", "code", "native")


def leaves(o, path=()):
    if isinstance(o, dict):
        for k in sorted(o):
            yield from leaves(o[k], path + (k,))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, path + (i,))
    else:
        yield path, o


def diff(a, b):
    la, lb = dict(leaves(a)), dict(leaves(b))
    out = []
    for p in sorted(set(la) | set(lb), key=str):
        if la.get(p, "<missing>") != lb.get(p, "<missing>"):
            out.append((p, la.get(p, "<missing>"), lb.get(p, "<missing>")))
    return out


d = diff(ref, cand)
non_timing = [x for x in d if x[0][0] not in TIMING]
print("leaves in reference:", len(dict(leaves(ref))), "candidate:", len(dict(leaves(cand))))
print("differing leaves:", len(d), "of which outside timing/provenance subtrees:", len(non_timing))
for p, a, b in non_timing:
    print("  ", ".".join(map(str, p)), ":", a, "->", b)
print("provenance/timing subtrees that differ:", sorted({x[0][0] for x in d if x[0][0] in TIMING}))

g = lambda r, *p: r.__getitem__(p[0]) if len(p) == 1 else g(r[p[0]], *p[1:])  # noqa: E731
print("\nclaims read from the leaves (reference -> candidate):")
for key in ("alarm_events", "stop_episodes", "alarm_frames", "frames", "advisory_frames"):
    print(f"  ride.{key}: {ref['ride'][key]} -> {cand['ride'][key]}")
print("  doubleT_platform advisory_frames:", ref["recordings"]["doubleT_platform"]["advisory_frames"], "->",
      cand["recordings"]["doubleT_platform"]["advisory_frames"])
print("  five_empty:", {k: (ref["five_empty"][k], cand["five_empty"][k]) for k in ref["five_empty"]})
print("  set_O inside_stop_frames:", ref["set_O"].get("inside_stop_frames"), "->", cand["set_O"].get("inside_stop_frames"))
objs = ref["set_O"]["objects"]
same = [k for k in objs if objs[k] == cand["set_O"]["objects"][k]]
print(f"  set_O objects: {len(objs)}; identical (every field): {len(same)}; differing: {sorted(set(objs) - set(same))}")
for k in ("long_low_on_rails", "small_on_rail", "thin_hanging"):
    if k in objs:
        print(f"    {k}: stop_frames {objs[k].get('stop_frames')} first_stop_m {objs[k].get('first_stop_m')} "
              f"(candidate {cand['set_O']['objects'][k].get('stop_frames')} {cand['set_O']['objects'][k].get('first_stop_m')})")
print("  doubleT_obstacle labelled hits:", ref["recordings"]["doubleT_obstacle"].get("labelled"),
      "->", cand["recordings"]["doubleT_obstacle"].get("labelled"))
print("  recordings identical except advisory/alarm: ", {
    k: [f for f in ref["recordings"][k] if ref["recordings"][k][f] != cand["recordings"][k].get(f)]
    for k in ref["recordings"]})
print("  set_F_straight identical:", ref["set_F_straight"] == cand["set_F_straight"],
      "; differing leaves under set_F_straight:", [".".join(map(str, p)) for p, a, b in non_timing if p[0] == "set_F_straight"])
print("  gate.passed:", ref["gate"]["passed"], cand["gate"]["passed"], " allow:", cand["gate"]["allow"],
      " worse_gated:", cand["gate"]["worse_gated"], " missing_gated:", cand["gate"]["missing_gated"])
print("  config sha256 / file_sha256 equal:", ref["config"]["sha256"] == cand["config"]["sha256"], ref["config"]["file_sha256"] == cand["config"]["file_sha256"], "; code commits:", ref["code"]["commit"][:7], cand["code"]["commit"][:7])

# positive controls
print("\npositive controls:")
sw = diff(cand, ref)
num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)  # noqa: E731
pairs = [((p, a, b), (p2, a2, b2)) for (p, a, b), (p2, a2, b2) in zip(d, sw) if p == p2 and num(a) and num(b)]
sign_ok = all((b - a) == -(b2 - a2) for (p, a, b), (p2, a2, b2) in pairs)
print("  (a) swapped comparison lists the same differing leaves:", [x[0] for x in sw] == [x[0] for x in d],
      f"; all {len(pairs)} numeric differences flip sign:", sign_ok)
mut = copy.deepcopy(cand)
mut["ride"]["frames"] += 1                       # a leaf that is equal in both reports
dm = diff(ref, mut)
print("  (b) one equal number changed in a copy (ride.frames +1): differing leaves", len(d), "->", len(dm),
      "(+1 expected)")
mut2 = copy.deepcopy(cand)
mut2["set_O"]["objects"]["small_on_rail"]["stop_frames"] -= 1
print("  (c) one set O STOP-frame count lowered by 1 in a copy: set O objects identical?",
      ref["set_O"]["objects"] == mut2["set_O"]["objects"], "(False expected)")
