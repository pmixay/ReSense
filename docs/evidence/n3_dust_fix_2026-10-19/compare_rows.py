"""Compare two dust-battery raw JSONL.gz files row by row on every non-timing field.
Timing fields: timing_ms, health.latency_p95_ms, and wall-clock latency health messages / levels
are reported separately (they depend on host load, not on the detector)."""
import gzip, json, sys

LAT = "latency p95"


def strip(r):
    r = json.loads(json.dumps(r))
    r.pop("timing_ms", None)
    h = r.get("health") or {}
    h.pop("latency_p95_ms", None)
    msgs = h.get("messages", [])
    lat = [m for m in msgs if m.startswith(LAT)]
    h["messages"] = [m for m in msgs if not m.startswith(LAT)]
    if lat:   # a latency-only warning: its level is wall-clock; drop the level fields for both sides
        h.pop("level", None)
    if "dust_guard" in h:
        pass
    return r, bool(lat)


def main(a, b):
    ra = [json.loads(l) for l in gzip.open(a, "rt")]
    rb = [json.loads(l) for l in gzip.open(b, "rt")]
    assert len(ra) == len(rb), (len(ra), len(rb))
    diff, lat = [], 0
    for x, y in zip(ra, rb):
        sx, lx = strip(x)
        sy, ly = strip(y)
        lat += lx or ly
        if lx != ly:   # the latency warning appears on one side only: compare without levels
            sx["health"].pop("level", None); sy["health"].pop("level", None)
        if sx != sy:
            diff.append(x["frame"])
    print(json.dumps({"a": a, "b": b, "rows": len(ra), "non_timing_differences": len(diff),
                      "first_differing_frames": diff[:10], "rows_with_latency_warning": lat}))
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
