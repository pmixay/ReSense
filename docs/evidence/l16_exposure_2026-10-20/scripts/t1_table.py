"""T1 table from t1_probe.py outputs: per recording, the first 10 frames' shares and directional_axes cue, and the
identity of each probed run's records with a plain run's (every field except the timing ones).

    python -I t1_table.py <dir with <name>.t1.json, <name>_probe.jsonl, <name>_plain.jsonl> <name> ... > table.txt
"""
import json
import sys

TIMING = {"decode_ms", "detect_ms", "total_ms"}


def load(p):
    return [{k: v for k, v in json.loads(line).items() if k not in TIMING} for line in open(p)]


def ax(v):
    if v is None:
        return "none"
    j = max(range(3), key=lambda k: abs(v[k]))
    return ("+" if v[j] > 0 else "-") + "XYZ"[j]


d = sys.argv[1]
print(f"{'recording':40s} {'frames':>6s} {'z>0 min/max':>15s} {'x<0 min/max':>15s} "
      f"{'sample pos min (x,y,z)':>26s} {'1-sided max':>11s} {'cue':>10s} {'locked':>7s} {'conflict':>8s} identity")
for name in sys.argv[2:]:
    t = json.load(open(f"{d}/{name}.t1.json"))
    fr = t["frames"]
    zp = [r["z_pos"] for r in fr]
    xn = [r["x_neg"] for r in fr]
    sp = [r["sample_pos"] for r in fr]
    one = max(max(max(p, 1 - p) for p in s) for s in sp)
    cues = sorted({ax(r["cue_forward"]) for r in fr})
    locked = sorted({ax(r["locked_forward"]) for r in fr})
    conflict = sum(r["orientation_conflict"] for r in fr)
    a, b = load(f"{d}/{name}_probe.jsonl"), load(f"{d}/{name}_plain.jsonl")
    same = "identical" if a == b else f"DIFFER ({sum(x != y for x, y in zip(a, b))} of {len(a)})"
    smin = [min(s[k] for s in sp) for k in range(3)]
    print(f"{name:40s} {len(fr):6d} {min(zp):7.4f}/{max(zp):7.4f} {min(xn):7.4f}/{max(xn):7.4f} "
          f"{'(' + ', '.join(f'{v:.3f}' for v in smin) + ')':>26s} {one:11.4f} {','.join(cues):>10s} "
          f"{','.join(locked):>7s} {conflict:8d} {same} ({len(a)} rows)")
