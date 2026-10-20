"""Falcon results of falcon_pair.py (P4 review of H′ and the Falcon clear-distance model, 20.10).

1. identity of the hooked shipped replica (``on``) with the committed shipped run (every non-timing field; the
   ``.x.jsonl`` track records too);
2. H′ off vs shipped: every frame whose decision, detections or warnings differ;
3. what H′ did on the whole recording (from the read-only hook): frames where the check ran with a final mount,
   clusters looked at, clusters whose model / mount disagreement exceeded the threshold, clusters made advisory;
4. attribution of every differing frame: the clusters H′ made advisory in that frame (on) against the off run's
   STOP detections in that frame (same distance and lateral within 0.05 m: the same cluster) and the off run's
   reporting track (its id, hits, the cluster);
5. the clear-distance model, in the node's own non-legacy path: decisions of all four variants against the
   detector's, frames where falcon_prime and unknown give a different clear distance, its largest value, and
   every frame where the reported clear distance reaches beyond a reported detection or warning.

    falcon_analyse.py <pair prefix> <shipped l16.jsonl.xz> <shipped l16.x.jsonl.xz>
"""
import json
import lzma
import sys
from collections import Counter

TIMING = {"decode_ms", "detect_ms", "total_ms"}


def load(p):
    with (lzma.open(p, "rt") if p.endswith(".xz") else open(p)) as f:
        return [json.loads(line) for line in f]


def strip(r):
    return {k: v for k, v in r.items() if k not in TIMING}


def key(r):
    return (r["decision"], r["dets"], r["warns"])


def main():
    pre, ref_p, refx_p = sys.argv[1:4]
    on, off, ref = load(pre + ".on.jsonl"), load(pre + ".off.jsonl"), load(ref_p)
    onx, offx = load(pre + ".on.x.jsonl"), load(pre + ".off.x.jsonl")
    with lzma.open(refx_p, "rt") as f:
        refx_lines = f.read().splitlines()
    with open(pre + ".on.x.jsonl") as f:
        onx_lines = f.read().splitlines()
    hrec, crec = load(pre + ".h.jsonl"), load(pre + ".c.jsonl")
    meta = json.load(open(pre + ".meta.json"))
    print("## 1. identity: hooked shipped replica vs committed shipped run")
    print(f"frames {len(on)} / committed {len(ref)}; stream found {meta['found']} kept {meta['kept']} lost {meta['lost']}; "
          f"bytes {meta['bytes']}")
    nd = sum(strip(a) != strip(b) for a, b in zip(on, ref))
    print(f"non-timing fields differ: {nd} rows; .x.jsonl lines equal: "
          f"{sum(a == b for a, b in zip(onx_lines, refx_lines))} of {len(refx_lines)}")
    print(f"replica calls into the clear-distance model during process: {meta['replica_calls']} "
          f"(positive control, the node path with the counters up: {meta['counter_control']})")
    print("\n## 2. H′ off vs shipped: frames with a different decision, detections or warnings")
    diff = [i for i, (a, b) in enumerate(zip(on, off)) if key(a) != key(b)]
    other = [i for i, (a, b) in enumerate(zip(on, off)) if key(a) == key(b) and strip(a) != strip(b)]
    trans = Counter(f"{on[i]['decision']}->{off[i]['decision']}" for i in diff)
    print(f"{len(diff)} frames: {diff}; transitions shipped->off {dict(trans)}; other non-timing only: {len(other)} {other[:20]}")
    stop_on = {r["i"] for r in on if r["decision"] == "STOP"}
    stop_off = {r["i"] for r in off if r["decision"] == "STOP"}
    print(f"STOP frames shipped {len(stop_on)}, off {len(stop_off)}; STOP only with H′ on: {sorted(stop_on - stop_off)}; "
          f"STOP only with H′ off: {sorted(stop_off - stop_on)}")
    print("\n## 3. what H′ did (shipped replica, read-only hook)")
    ran = [h for h in hrec if any(h["ok"])]
    rows = [(h["i"], r) for h in hrec for r in h["rows"]]
    over = [(i, r) for i, r in rows if r["diff"] > r["thr"]]
    dem = [(i, r) for i, r in rows if r["demoted"]]
    print(f"calls {sum(h['calls'] for h in hrec)} in {len(hrec)} frames; with a final mount {len(ran)} frames "
          f"(first {ran[0]['i'] if ran else None}); mount status counts {dict(Counter(s for h in hrec for s in h['status']))}")
    print(f"clusters looked at {len(rows)}; model/mount disagreement over the threshold {len(over)} in frames "
          f"{sorted({i for i, _ in over})}; made advisory {len(dem)} in frames {sorted({i for i, _ in dem})}")
    for i, r in over:
        print(f"   frame {i}: d {r['d']} lat {r['lat']} {r['kind']} n {r['n']} rail_z {r['rail_z']} plane {r['plane']} "
              f"|diff| {r['diff']} > thr {r['thr']}; heights above the plane {r['hm_min']}..{r['hm_max']} (top {r['top']}); "
              f"above the model rail head {r['h_model_min']}..{r['h_model_max']}; demoted {r['demoted']}")
    print("\n## 4. attribution of every differing frame")
    for i in diff:
        dm = [r for j, r in dem if j == i]
        same = []
        for d in off[i]["dets"]:
            m = [r for r in dm if abs(r["d"] - d["d"]) <= 0.05 and abs(r["lat"] - d["lat"]) <= 0.05]
            same.append((d["d"], d["lat"], bool(m)))
        trk = [(x["id"], x["hits"], x["kind"], x["d"], x["lat"], x["top"], x["hmin"]) for x in offx[i]["dets"]
               if x["zone"] == "gauge"]
        trk_on = [(x["id"], x["zone"], x["reason"], x["creason"], x["d"]) for x in onx[i]["dets"]]
        print(f"frame {i}: shipped {on[i]['decision']} -> off {off[i]['decision']}; H′ made advisory here: "
              f"{[(r['d'], r['lat']) for r in dm]}; off STOP detections (d, lat, = an H′ cluster): {same}; "
              f"off reporting tracks (id, hits, kind, d, lat, top, hmin): {trk}; shipped tracks: {trk_on}")
    print("\n## 5. the clear-distance model in the node's non-legacy path")
    variants = ["conservative.falcon_prime", "conservative.unknown", "small_candidate.falcon_prime",
                "small_candidate.unknown"]
    bad = [c["i"] for c in crec if any(c[v]["decision"] != c["decision"] for v in variants) or c["decision"] != on[c["i"]]["decision"]]
    print(f"frames whose decision differs between the detector record and any variant: {len(bad)} {bad[:20]}")
    for pol in ("conservative", "small_candidate"):
        a, b = f"{pol}.falcon_prime", f"{pol}.unknown"
        dif = [c for c in crec if c[a]["clear"] != c[b]["clear"]]
        vals = Counter(c[a]["clear"] for c in crec)
        print(f"{pol}: clear differs (model on vs off) in {len(dif)} frames; model off: clear > 0 in "
              f"{sum(c[b]['clear'] > 0 for c in crec)} frames; model on: max {max(c[a]['clear'] for c in crec)}, "
              f"frames at 48.2 {vals.get(48.2, 0)}, clear > 0 in {sum(c[a]['clear'] > 0 for c in crec)}, "
              f"by decision {dict(Counter(on[c['i']]['decision'] for c in dif))}; "
              f"max monitored_small {max((c[a]['monitored_small'] or 0) for c in crec)}")
        beyond = []
        for c in crec:
            r = on[c["i"]]
            near = [d["d"] for d in r["dets"] + r["warns"]]
            if near and c[a]["clear"] > min(near):
                beyond.append((c["i"], r["decision"], c[a]["clear"], min(near)))
        print(f"   frames where the model-on clear distance reaches beyond a reported detection or warning: "
              f"{len(beyond)} {beyond[:10]}")
        det_beyond = [(c["i"], c["detector_clear"], min(d["d"] for d in on[c["i"]]["dets"] + on[c["i"]]["warns"]))
                      for c in crec if on[c["i"]]["dets"] + on[c["i"]]["warns"]
                      and c["detector_clear"] > min(d["d"] for d in on[c["i"]]["dets"] + on[c["i"]]["warns"])]
        print(f"   (the detector's own clear distance beyond a detection or warning: {len(det_beyond)} {det_beyond[:10]})")


if __name__ == "__main__":
    main()
