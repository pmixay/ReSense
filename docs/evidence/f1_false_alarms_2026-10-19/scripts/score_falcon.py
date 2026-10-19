"""Score a Falcon run against the base run: the 12 attributed false STOP frames and the 1,360 others
(person-associated, falcon_full_2026-10-18/README.md); CAUTION/GO/STOP changes per frame."""
import json, sys
FALSE = {159, 2312, 2313, 2314} | set(range(4394, 4402))
base = [json.loads(l) for l in open(sys.argv[1])]
cand = [json.loads(l) for l in open(sys.argv[2])]
assert len(base) == len(cand) == 4443
stop_b = {r["i"] for r in base if r["decision"] == "STOP"}
R = stop_b - FALSE
stop_c = {r["i"] for r in cand if r["decision"] == "STOP"}
def same(i):
    b = [(d["d"], d["lat"]) for d in base[i]["dets"]]
    return any(abs(d["d"] - x) <= 0.5 and abs(d["lat"] - y) <= 0.5 for d in cand[i]["dets"] for x, y in b)
kept = sorted(i for i in R if i in stop_c and same(i))
lost = sorted(i for i in R if i not in kept)
new = sorted(stop_c - stop_b)
first = lambda rows, s: next(((r["i"], r["nearest"]) for r in rows if r["i"] in s and r["i"] > 2900), None)
trans = {}
for b, c in zip(base, cand):
    if b["decision"] != c["decision"]:
        k = f'{b["decision"]}->{c["decision"]}'
        trans[k] = trans.get(k, 0) + 1
out = {"base_stop": len(stop_b), "cand_stop": len(stop_c), "false_attributed_base": len(FALSE & stop_b),
       "false_attributed_remaining": sorted(FALSE & stop_c), "person_ref": len(R), "person_kept": len(kept),
       "person_lost": lost[:50], "n_person_lost": len(lost), "new_stop_frames": new[:50], "n_new_stop": len(new),
       "first_person_stop_base": first(base, R), "first_person_stop_cand": first(cand, set(kept)),
       "decision_transitions": trans,
       "caution_base": sum(r["decision"] == "CAUTION" for r in base),
       "caution_cand": sum(r["decision"] == "CAUTION" for r in cand)}
print(json.dumps(out, indent=1))
