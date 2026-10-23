"""Independent comparison of two gate row directories (per-frame jsonl of eval_real). Every key except clear
(health.clear_distance / clear_distance) and timing is compared recursively; reports lowered/raised clear rows.
--inject: positive control, flips one detection distance in one candidate row; must be reported as 1 differing row."""
import json, glob, os, sys, copy
A, B = sys.argv[1], sys.argv[2]; inject = "--inject" in sys.argv
SKIP_KEYS = {"timing_ms", "latency_ms", "latency_p95_ms", "wall_ms", "total_ms"}
def strip(o, path=""):
    if isinstance(o, dict):
        return {k: strip(v, path + "/" + k) for k, v in o.items()
                if k not in SKIP_KEYS and k not in ("clear_distance",) }
    if isinstance(o, list): return [strip(v, path) for v in o]
    return o
def clear_of(r): return r.get("clear_distance", (r.get("health") or {}).get("clear_distance"))
tot = diff = up = down = 0; fields = {}; per = {}
for fa in sorted(glob.glob(A + "/*.jsonl")):
    fb = os.path.join(B, os.path.basename(fa)); ra = [json.loads(l) for l in open(fa)]; rb = [json.loads(l) for l in open(fb)]
    assert len(ra) == len(rb), fa
    if inject and os.path.basename(fa) == "cloud_with_fake_obj.jsonl":
        rb[100]["n_points"] = rb[100]["n_points"] + 1
    d = u = w = 0
    for a, b in zip(ra, rb):
        tot += 1
        sa, sb = strip(a), strip(b)
        if sa != sb:
            diff += 1; d += 1
            for k in set(sa) | set(sb):
                if sa.get(k) != sb.get(k):
                    # latency messages: health.messages/level may carry the machine-speed warning
                    fields[k] = fields.get(k, 0) + 1
        ca, cb = clear_of(a), clear_of(b)
        if ca is None or cb is None: continue
        if cb > ca + 1e-9: up += 1; u += 1
        elif cb < ca - 1e-9: down += 1; w += 1
    per[os.path.basename(fa)[:-6]] = (len(ra), d, u, w)
print(json.dumps({"rows": tot, "rows_other_fields_differ": diff, "fields": fields, "clear_raised": up, "clear_lowered": down}))
for k, v in per.items(): print(f"  {k:40s} rows={v[0]:5d} other_differ={v[1]:4d} raised={v[2]} lowered={v[3]}")
