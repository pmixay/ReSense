"""Compare the H1 physical-replay reports (docs/evidence/h1_reference_2026-10-19/physical_e.py output).

    python physical_compare.py <A.json> <B.json> [label]

Stationary: hit flag and detection payload per scan (32 cases x 14); outside: the 280 cases; moving: hit and payload per
scan (12 cases x 56) and the distance from which every scan is a hit (``continuous_from``).
"""
import json
import sys

a, b = (json.load(open(p)) for p in sys.argv[1:3])
label = sys.argv[3] if len(sys.argv) > 3 else ""


def payload(rows):
    return [json.dumps(r["detections"], sort_keys=True) for r in rows]


dh = dd = n = mh = md = mn = 0
for x, y in zip(a["full"], b["full"]):
    assert (x["distance"], x["lateral"], x["top"], x["absorbing"]) == (y["distance"], y["lateral"], y["top"], y["absorbing"])
    for r, s, pr, ps in zip(x["rows"], y["rows"], payload(x["rows"]), payload(y["rows"])):
        n += 1
        dh += r["hit"] != s["hit"]
        dd += pr != ps
for x, y in zip(a["moving"], b["moving"]):
    for r, s, pr, ps in zip(x["rows"], y["rows"], payload(x["rows"]), payload(y["rows"])):
        mn += 1
        mh += r["hit"] != s["hit"]
        md += pr != ps
ca, cb = [x["continuous_from"] for x in a["moving"]], [y["continuous_from"] for y in b["moving"]]
print(f"{label}: stationary rows {n}: hit differs {dh}, detection payload differs {dd} | moving rows {mn}: hit differs {mh}, "
      f"payload differs {md} | outside cases identical {a['outside'] == b['outside']} | summaries {a['summary']} / {b['summary']}")
print("   continuous_from A", ca)
print("   continuous_from B", cb, "| equal" if ca == cb else f"| max difference {max(abs((u or 0)-(v or 0)) for u, v in zip(ca, cb)):.1f} m")
