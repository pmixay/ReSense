#!/usr/bin/env python3
"""Compare a run_new_recordings.sh work folder with the committed pre-release (1.1.0) evidence.

    compare_new_recordings.py <work dir>

Each line is PASS, DIFF (the release behaves differently: a finding, not an error) or MISSING (step not run).
Decisions are compared frame by frame against the committed per-frame records; score and gauge files field by
field. Wall-clock fields (timing, latency health lines) are not compared.
"""
import json
import sys
import tarfile
from pathlib import Path

EV = Path(__file__).resolve().parents[2]
ROW_SKIP = {"decode_ms", "detect_ms", "total_ms", "msgs", "level"}


def committed_jsonl(tar, member):
    with tarfile.open(tar) as t:
        return [json.loads(x) for x in t.extractfile(member).read().decode().splitlines()]


def decisions(rows):
    return [r["decision"] for r in rows]


def line(ok, name, detail):
    status = "MISSING" if ok is None else ("PASS" if ok else "DIFF")
    print(f"{status:7s} {name}: {detail}")
    return ok


def main():
    w = Path(sys.argv[1])
    res = []
    f = w / "freeze_verify.txt"
    txt = f.read_text().strip() if f.exists() else ""
    res.append(line(("PASS" in txt.splitlines()[0]) if txt else None, "detector_freeze verify",
                    txt.splitlines()[0] if txt else "not run"))
    tar = EV / "synthetic_labels_2026-10-17/runs/detector_runs.tar.xz"
    for b in ("synthetic_platform", "synthetic_switch", "synthetic_tunnels"):
        p = w / f"synth_{b}.jsonl"
        if not p.exists():
            res.append(line(None, f"synthetic {b}", "not run"))
            continue
        new, ref = decisions(map(json.loads, open(p))), decisions(committed_jsonl(tar, f"v110_{b}.jsonl"))
        same = sum(a == b_ for a, b_ in zip(new, ref))
        res.append(line(new == ref, f"synthetic {b} decisions", f"{same}/{len(ref)} frames equal"))
    p = w / "score_platform.json"
    ref = json.load(open(EV / "synthetic_labels_2026-10-17/score_platform_0-314_v110.json"))
    if p.exists():
        new = json.load(open(p))
        res.append(line(new == ref, "synthetic_platform score (0-314)",
                        "person first STOP " + str(new["objects"]["obj03"]["first_stop_d"]) + " m, unmatched "
                        + str(new["unmatched_stop_frames"])))
    else:
        res.append(line(None, "synthetic_platform score", "not run"))
    p = w / "falcon_full.jsonl"
    if p.exists() and (w / "falcon_full.meta.json").exists():   # the meta file is written when the stream ends
        new = decisions(map(json.loads, open(p)))
        ref = decisions(committed_jsonl(EV / "falcon_full_2026-10-18/falcon_full_runs.tar.xz", "falcon_full_v110.jsonl"))
        same = sum(a == b_ for a, b_ in zip(new, ref))
        res.append(line(new == ref, "Falcon whole recording decisions", f"{same}/{len(ref)} frames equal ({len(new)} run)"))
        m = json.load(open(w / "falcon_full.meta.json"))
        res.append(line(m["lost"] == 0 and m["kept"] == m["found"] == 4443, "Falcon stream complete",
                        f"{m['kept']} of {m['found']} messages, {m['lost']} lost"))
    else:
        res.append(line(None, "Falcon whole recording", "not run"))
    p = w / "switch/compare.json"
    ref = json.load(open(EV / "falcon_switch_2026-10-18/v110/compare.json"))
    if p.exists():
        new = json.load(open(p))
        for o in ("p2f", "f2p"):
            only_level = all(set(d[1]) <= {"level"} for d in new[o]["differences"])
            ok = only_level and new[o]["decisions"] == ref[o]["decisions"] and new[o]["resets"] == ref[o]["resets"]
            res.append(line(ok, f"switch {o}", f"decisions {new[o]['decisions']}, resets {new[o]['resets']}, "
                            f"field differences only wall-clock 'level': {only_level}"))
    else:
        res.append(line(None, "switch", "not run"))
    gdir, gref = w / "gauge", EV / "gauge_stability_2026-10-18/v110"
    for p in sorted(gdir.glob("measure_*.json")) if gdir.exists() else []:
        bag = p.stem[len("measure_"):]
        new, ref = json.load(open(p)), json.load(open(gref / p.name))
        for d in (new, ref):
            d.pop("track"), d.pop("poses")
        res.append(line(new == ref, f"gauge {bag}", f"trusted range p50 {new['range']['p50']} m, blinks {new['blinks']}"))
        h = gdir / f"honesty_{bag}.json"
        if h.exists():
            hn, hr = json.load(open(h)), json.load(open(gref / h.name))
            hn.pop("run"), hr.pop("run")
            res.append(line(hn == hr, f"gauge honesty {bag}", f"reported range > 1.05 m off: {hn['inside_over_1.05m']} "
                            f"(committed {hr['inside_over_1.05m']})"))
    if not (gdir.exists() and list(gdir.glob("measure_*.json"))):
        res.append(line(None, "gauge", "not run"))
    print(f"\n{sum(r is True for r in res)} PASS, {sum(r is False for r in res)} DIFF, {sum(r is None for r in res)} MISSING")


if __name__ == "__main__":
    main()
