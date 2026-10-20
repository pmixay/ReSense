#!/usr/bin/env python3
"""Cold start of the detector on a cut of the Falcon recording, against the whole-recording record.

    RESENSE_REPO=<tree> OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 \\
    coldstart_compare.py --bag BAG_DIR_OR_DB3 --record l16.jsonl.xz --first-frame A [--skip K] \\
        [--last-frame L] --out PREFIX

Replays the PointCloud2 messages of the bag, in receive-time order, through the judge's ``NodeReplica``
(``judge_runner``, unmodified, taken from the evaluated tree: node decode, continuity rules, decision rule)
with a detector that has seen nothing before the first replayed message. The k-th message of the bag is
frame ``A + k`` of the recording (``A`` = ``--first-frame``, the bag's first frame number from its manifest).
``--skip K`` drops the first K messages of the bag before the replay, to try a later start on a wider bag.

The rows are compared with the record of the same frames (the whole 4,443-frame run of the same source,
``docs/evidence/l16_acceptance_2026-10-20/out/falcon/l16.jsonl.xz``). Nothing in the detector is touched.
Writes ``PREFIX.jsonl`` (the replay rows, with ``frame`` = number in the recording) and ``PREFIX.summary.json``.
"""
from __future__ import annotations

import argparse
import json
import lzma
import os
import sys
import time

REPO = os.environ.get("RESENSE_REPO")
if not REPO:
    sys.exit("set RESENSE_REPO to the tree being evaluated")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "docs/evidence/judgement_2026-10-13/scripts"))
import judge_runner as jr  # noqa: E402
from resense import _native  # noqa: E402

TIMING = {"decode_ms", "detect_ms", "total_ms"}
HEALTH_LATENCY = "latency"


def comparable(row: dict) -> dict:
    """The row without wall-clock timing and without what the latency budget drives (health level / message)."""
    out = {k: v for k, v in row.items() if k not in TIMING and k not in ("i", "frame")}
    out["msgs"] = [m for m in row.get("msgs", []) if HEALTH_LATENCY not in m]
    return out


def det_key(d: dict) -> tuple:
    return (d["d"], d["lat"], d["n"], d["zone"], d["kind"])


def stop_runs(decisions: list[str], first: int) -> list[tuple[int, int]]:
    """(first, last) frame numbers of every run of consecutive STOP frames"""
    runs: list[list[int]] = []
    for k, d in enumerate(decisions):
        if d == "STOP":
            if runs and runs[-1][1] == first + k - 1:
                runs[-1][1] = first + k
            else:
                runs.append([first + k, first + k])
    return [(r[0], r[1]) for r in runs]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bag", required=True)
    ap.add_argument("--record", required=True, help="whole-recording per-frame record (.jsonl or .jsonl.xz)")
    ap.add_argument("--first-frame", type=int, required=True, help="frame number of the bag's first message")
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--last-frame", type=int, default=0, help="stop after this frame number (default: the bag's end)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    opener = lzma.open if a.record.endswith(".xz") else open
    with opener(a.record, "rt") as fh:
        record = [json.loads(line) for line in fh]
    assert [r["i"] for r in record] == list(range(len(record))), "record rows must be numbered 0..N-1"

    rep = jr.NodeReplica()
    rows, t0 = [], time.time()
    k = 0
    with open(a.out + ".jsonl", "w") as out:
        for db3 in jr.db3_files(a.bag):
            for ts, topic, raw in jr.iter_raw(db3):
                frame = a.first_frame + k
                k += 1
                if k - 1 < a.skip:
                    continue
                if a.last_frame and frame > a.last_frame:
                    break
                msg, stamp, res, dec_ms, det_ms = rep.process_raw(raw, topic, len(rows))
                r = jr.record(len(rows), ts / 1e9, stamp, res, dec_ms, det_ms, msg.header.frame_id, topic)
                r["frame"] = frame
                rows.append(r)
                out.write(json.dumps(r) + "\n")
    first = a.first_frame + a.skip
    ref = record[first:first + len(rows)]
    assert len(ref) == len(rows), "the bag runs past the record"

    # the bag and the record must be the same frames: receive time and header stamp (4 decimals in the record)
    clock = [(i, abs(r["bag_t"] - q["bag_t"]), abs(r["stamp"] - q["stamp"])) for i, (r, q) in enumerate(zip(rows, ref))]
    mismatched_clock = [i for i, dt, ds in clock if dt > 2e-4 or ds > 2e-4]

    dec = [r["decision"] for r in rows]
    ref_dec = [q["decision"] for q in ref]
    differ_dec = [first + i for i, (x, y) in enumerate(zip(dec, ref_dec)) if x != y]
    differ_row = [first + i for i, (x, y) in enumerate(zip(rows, ref)) if comparable(x) != comparable(y)]

    def converged(differ: list[int]) -> int | None:
        """first frame from which no later frame differs (None if the last frame still differs)"""
        if not differ:
            return first
        return None if differ[-1] == first + len(rows) - 1 else differ[-1] + 1

    runs, ref_runs = stop_runs(dec, first), stop_runs(ref_dec, first)
    t_first = rows[0]["bag_t"]

    def first_stop(rs, rr):
        if not rs:
            return None
        f = rs[0][0]
        row = rr[f - first]
        return {"frame": f, "s_from_replay_start": round(row["bag_t"] - t_first, 2),
                "nearest_m": row["nearest"], "run_frames": rs[0][1] - rs[0][0] + 1}

    new_stop = [first + i for i, (x, y) in enumerate(zip(dec, ref_dec)) if x == "STOP" and y != "STOP"]
    missed_stop = [first + i for i, (x, y) in enumerate(zip(dec, ref_dec)) if x != "STOP" and y == "STOP"]
    fault = [first + i for i, d in enumerate(dec) if d == "FAULT"]
    ref_fault = [first + i for i, d in enumerate(ref_dec) if d == "FAULT"]
    mount_ok = next((r["frame"] for r in rows if r["mount"] == "ok"), None)
    total_ms = sorted(r["decode_ms"] + r["detect_ms"] for r in rows)
    summary = {
        "bag": a.bag, "first_frame_of_bag": a.first_frame, "skip": a.skip, "replay_first_frame": first,
        "replay_last_frame": first + len(rows) - 1, "frames": len(rows),
        "replay_seconds": round(rows[-1]["bag_t"] - rows[0]["bag_t"], 2),
        "frames_with_wrong_receive_time_or_stamp": mismatched_clock,
        "decisions_replay": {d: dec.count(d) for d in ("GO", "CAUTION", "STOP", "FAULT")},
        "decisions_record_same_frames": {d: ref_dec.count(d) for d in ("GO", "CAUTION", "STOP", "FAULT")},
        "frames_with_different_decision": len(differ_dec),
        "different_decision_frames_first_40": differ_dec[:40],
        "decision_identical_from_frame": converged(differ_dec),
        "frames_with_any_different_nonlatency_field": len(differ_row),
        "row_identical_from_frame": converged(differ_row),
        "first_stop_replay": first_stop(runs, rows),
        "first_stop_record": first_stop(ref_runs, ref),
        "stop_runs_replay": runs[:12], "stop_runs_record": ref_runs[:12],
        "stop_frames_replay": dec.count("STOP"), "stop_frames_record": ref_dec.count("STOP"),
        "stop_in_replay_not_in_record": new_stop, "stop_in_record_not_in_replay": missed_stop,
        "fault_frames_replay": fault, "fault_frames_record": ref_fault,
        "mount_ok_from_frame_replay": mount_ok,
        "mount_ok_from_frame_record": next((first + i for i, q in enumerate(ref) if q["mount"] == "ok"), None),
        "first_rows": [{"frame": r["frame"], "decision": r["decision"], "level": r["level"], "mount": r["mount"],
                        "nearest": r["nearest"], "msgs": r["msgs"][:2]} for r in rows[:6]],
        "resets": rep.resets, "decode_plus_detect_ms_median": round(total_ms[len(total_ms) // 2], 1),
        "decode_plus_detect_ms_max": round(total_ms[-1], 1), "wall_s": round(time.time() - t0, 1),
        "native": _native.status(),
        "resense_repo": REPO}
    with open(a.out + ".summary.json", "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps({k: summary[k] for k in (
        "replay_first_frame", "frames", "frames_with_different_decision", "decision_identical_from_frame",
        "row_identical_from_frame", "first_stop_replay", "first_stop_record", "stop_in_replay_not_in_record",
        "stop_in_record_not_in_replay", "fault_frames_replay", "mount_ok_from_frame_replay", "native",
        "frames_with_wrong_receive_time_or_stamp", "wall_s")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
