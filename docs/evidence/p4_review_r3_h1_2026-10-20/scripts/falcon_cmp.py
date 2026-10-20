"""Per-frame non-timing comparison of two falcon_trace.py runs (``<prefix>.jsonl`` and ``<prefix>.x.jsonl``).

A row is the same when every field except decode_ms / detect_ms / total_ms is equal, after the latency
health message is removed; rows that then differ only in level / dlevel are counted as latency-only (the
health level is clock-driven), as cmp_frames.py does for the gate. Every frame whose decision, detections or
warnings differ is listed with both sides' STOP / CAUTION objects. The .x.jsonl track model and detection
clusters are compared per frame too.

    python falcon_cmp.py <reference prefix or .jsonl[.xz]> <candidate prefix>
"""
import json
import lzma
import sys

TIMING = {"decode_ms", "detect_ms", "total_ms"}


def rows(path):
    op = lzma.open if path.endswith(".xz") else open
    with op(path, "rt") as f:
        return [json.loads(line) for line in f]


def resolve(p, ext):
    for cand in (p + ext, p + ext + ".xz") + ((p,) if ext == ".jsonl" else ()):
        try:
            open(cand).close()
            return cand
        except OSError:
            continue
    raise SystemExit(f"no {ext} for {p}")


def norm(r):
    r = {k: v for k, v in r.items() if k not in TIMING}
    r["msgs"] = [m for m in r.get("msgs", []) if "latency" not in m]
    return r


def short(dets):
    return [(d["d"], d["lat"], d.get("kind", ""), d.get("reason", ""), d.get("zone", "")) for d in dets]


def main():
    A, B = sys.argv[1], sys.argv[2]
    a, b = rows(resolve(A, ".jsonl")), rows(resolve(B, ".jsonl"))
    print(f"rows {len(a)} vs {len(b)}")
    diff, lat, ddw = [], 0, []
    for x, y in zip(a, b):
        nx, ny = norm(x), norm(y)
        if nx == ny:
            continue
        if {k: v for k, v in nx.items() if k not in ("level", "dlevel")} == \
                {k: v for k, v in ny.items() if k not in ("level", "dlevel")}:
            lat += 1
            continue
        diff.append(x["i"])
        if (x["decision"], x["dets"], x["warns"]) != (y["decision"], y["dets"], y["warns"]):
            ddw.append((x, y))
    print(f"differ (non-timing) {len(diff)}; latency-level only {lat}; differ in decision/dets/warns {len(ddw)}")
    print("frames differing (non-timing):", diff[:200])
    stop_a = {r["i"] for r in a if r["decision"] == "STOP"}
    stop_b = {r["i"] for r in b if r["decision"] == "STOP"}
    print(f"STOP rows {len(stop_a)} -> {len(stop_b)}; lost {sorted(stop_a - stop_b)}; added {sorted(stop_b - stop_a)}")
    for x, y in ddw:
        print(f"  frame {x['i']}: {x['decision']} -> {y['decision']}")
        print(f"      ref dets {short(x['dets'])} warns {short(x['warns'])}")
        print(f"      new dets {short(y['dets'])} warns {short(y['warns'])}")
    try:
        xa, xb = rows(resolve(A, ".x.jsonl")), rows(resolve(B, ".x.jsonl"))
    except SystemExit:
        print("x rows: not available on both sides")
        return
    tdiff = [p["i"] for p, q in zip(xa, xb) if p["track"] != q["track"]]
    xdiff = [p["i"] for p, q in zip(xa, xb) if p != q]
    print(f"x rows {len(xa)} vs {len(xb)}; track model differs in {len(tdiff)} frames {tdiff[:20]}; "
          f"any x field differs in {len(xdiff)} frames {xdiff[:50]}")


if __name__ == "__main__":
    main()
