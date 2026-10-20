"""T1 table (rerun on the L16-repaired code) from t1_probe_p4.py outputs.

Per recording, over the first 10 frames: min/max share of returns with z > 0 and with x < 0 (all returns, vehicle frame as
the calibrator receives them), the per-axis positive shares of directional_axes' own sample (min over frames) and the
largest one-sided share, the cue directional_axes(xyz) gives per frame, the calibrator's locked forward axis, the first
frame at which the calibrator reports ``orientation_confirmed`` (and the status / mapping / message there), the number of
frames with ``orientation_conflict``, and whether the probed run's records equal a plain run's (all fields but timing).

    python -I t1_table_p4.py <dir with <name>.t1.json, <name>_probe.jsonl, <name>_plain.jsonl> <name> ...
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
for name in sys.argv[2:]:
    t = json.load(open(f"{d}/{name}.t1.json"))
    fr = t["frames"]
    sp = [r["sample_pos"] for r in fr]
    one = max(max(max(p, 1 - p) for p in s) for s in sp)
    first = next((r["frame"] for r in fr if r["orientation_confirmed"]), None)
    a, b = load(f"{d}/{name}_probe.jsonl"), load(f"{d}/{name}_plain.jsonl")
    same = "identical" if a == b else f"DIFFER ({sum(x != y for x, y in zip(a, b))} of {len(a)})"
    print(f"{name}: {len(fr)} frames, returns/frame {min(r['n'] for r in fr)}-{max(r['n'] for r in fr)}")
    print(f"  share z>0 {min(r['z_pos'] for r in fr):.4f}-{max(r['z_pos'] for r in fr):.4f}   "
          f"share x<0 {min(r['x_neg'] for r in fr):.4f}-{max(r['x_neg'] for r in fr):.4f}   "
          f"sample pos min (x,y,z) ({', '.join(f'{min(s[k] for s in sp):.3f}' for k in range(3))})   1-sided max {one:.4f}")
    print(f"  directional_axes cue per frame: {sorted({ax(r['cue_forward']) for r in fr})}   "
          f"calibrator's own calls: {[ (c['frame'], ax(c['forward']), ax(c['up'])) for c in t['calibrator_calls']]}   "
          f"locked forward: {sorted({ax(r['locked_forward']) for r in fr})}")
    print(f"  orientation_confirmed first at frame {first}; at frame 0: {fr[0]['orientation_confirmed']}, at frame 9: "
          f"{fr[-1]['orientation_confirmed']}; status {sorted({r['status'] for r in fr})}; mapping {sorted({r['orientation'] for r in fr})}; "
          f"conflict frames {sum(r['orientation_conflict'] for r in fr)}; messages {sorted({r['message'] for r in fr})}")
    print(f"  probed vs plain run: {same} ({len(a)} rows); decisions {sorted({r['decision'] for r in a})}")
