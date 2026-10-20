#!/usr/bin/env python3
"""Check a cut Falcon demo bag against sources that do not come from the cutting script.

    RESENSE_REPO=<tree> verify_bag.py --bag BAG_DIR --first-frame A --record l16.jsonl.xz \\
        [--manifest frames.tsv] [--inventory cache_inventory.json] [--original-metadata metadata.yaml] --out report.json

Reads the bag only through sqlite (not through the recovery code that wrote it) and compares, frame by frame:

1. ``metadata.yaml`` with the bag: message count, first receive time, duration, file name, QoS string;
   with ``--original-metadata`` (the organizers' ``metadata.yaml``) the ``/iv_points`` topic entry is equal.
2. The receive time and header stamp of message k with row ``A + k`` of the whole-recording record (made by
   a different run from the same archive), and the number of points the node decodes with ``n_points`` there.
3. ``--manifest``: frame number, receive time, header stamp, size and sha256 of every message.
4. ``--inventory``: the sha256 of the ``.npz`` that ``docs/evidence/n2_falcon_2026-10-18/cache_falcon.py`` wrote
   for the frame, which was made from the extracted 20.3 GB split read by sqlite itself, not by the recovery:
   the same decode and ``np.savez_compressed`` call is made here and the file's sha256 compared.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import os
import sqlite3
import struct
import sys
import tempfile

import numpy as np
import yaml

REPO = os.environ.get("RESENSE_REPO")
if not REPO:
    sys.exit("set RESENSE_REPO to the tree being evaluated")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "ros2_ws/src/resense_ros"))
from resense_ros import fastcloud  # noqa: E402


def header_stamp(data: bytes) -> float:
    sec, nsec = struct.unpack_from("<iI", data, 4)
    return sec + nsec * 1e-9


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bag", required=True)
    ap.add_argument("--first-frame", type=int, required=True)
    ap.add_argument("--record", required=True)
    ap.add_argument("--manifest", default="")
    ap.add_argument("--inventory", default="")
    ap.add_argument("--original-metadata", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    bad: dict[str, list] = {k: [] for k in ("record_bag_time", "record_stamp", "record_n_points", "manifest",
                                            "npz_sha256", "order")}
    meta = yaml.safe_load(open(os.path.join(a.bag, "metadata.yaml")))["rosbag2_bagfile_information"]
    db = os.path.join(a.bag, meta["relative_file_paths"][0])
    opener = lzma.open if a.record.endswith(".xz") else open
    with opener(a.record, "rt") as fh:
        record = [json.loads(line) for line in fh]
    manifest = None
    if a.manifest:
        lines = open(a.manifest).read().splitlines()
        manifest = [ln.split("\t") for ln in lines[1:]]
    inventory = json.load(open(a.inventory)) if a.inventory else None

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    topics = list(con.execute("SELECT id, name, type, serialization_format, offered_qos_profiles FROM topics"))
    rows = con.execute("SELECT id, topic_id, timestamp, data FROM messages ORDER BY timestamp, id")
    n = 0
    prev = None
    gaps = []
    npz_checked = 0
    with tempfile.TemporaryDirectory(prefix="verify_bag_") as tmp:
        for k, (mid, topic_id, ts, data) in enumerate(rows):
            n += 1
            frame = a.first_frame + k
            if mid != k + 1 or topic_id != topics[0][0]:
                bad["order"].append(frame)
            if prev is not None:
                gaps.append((ts - prev) / 1e9)
                if ts <= prev:
                    bad["order"].append(frame)
            prev = ts
            ref = record[frame]
            stamp = header_stamp(data)
            if abs(ref["bag_t"] - ts / 1e9) > 1e-4:
                bad["record_bag_time"].append(frame)
            if abs(ref["stamp"] - stamp) > 1e-4:
                bad["record_stamp"].append(frame)
            msg = fastcloud.parse_pointcloud2(data)
            xyz, inten, ring, n_raw, n_near = fastcloud.decode(fastcloud.packed(msg), 2.5, 250.0)
            if len(xyz) != ref["n_points"]:
                bad["record_n_points"].append(frame)
            if manifest is not None:
                m = manifest[k]
                if (int(m[0]), int(m[1]), int(m[3]), m[4]) != (frame, ts, len(data), hashlib.sha256(data).hexdigest()) \
                        or m[2] != f"{struct.unpack_from('<i', data, 4)[0]}.{struct.unpack_from('<I', data, 8)[0]:09d}":
                    bad["manifest"].append(frame)
            if inventory is not None:
                path = os.path.join(tmp, "f.npz")
                np.savez_compressed(path, xyz=xyz, inten=inten, ring=ring)
                digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
                npz_checked += 1
                entry = inventory[frame]
                assert entry["frame"] == frame
                if digest != entry["sha256"]:
                    bad["npz_sha256"].append(frame)
    con.close()

    report = {
        "bag": a.bag, "first_frame": a.first_frame, "messages": n, "topics_in_bag": [t[1] for t in topics],
        "metadata_message_count": meta["message_count"],
        "metadata_matches_bag": (
            meta["message_count"] == n and meta["topics_with_message_count"][0]["message_count"] == n
            and meta["files"][0]["message_count"] == n and meta["storage_identifier"] == "sqlite3"
            and meta["version"] == 5 and meta["topics_with_message_count"][0]["topic_metadata"]["offered_qos_profiles"]
            == topics[0][4] and meta["files"][0]["path"] == os.path.basename(db)),
        "receive_gap_s_min_median_max": [round(min(gaps), 4), round(sorted(gaps)[len(gaps) // 2], 4),
                                         round(max(gaps), 4)] if gaps else None,
        "frames_not_in_order": bad["order"],
        "frames_with_other_receive_time_than_record": bad["record_bag_time"],
        "frames_with_other_header_stamp_than_record": bad["record_stamp"],
        "frames_with_other_decoded_point_count_than_record": bad["record_n_points"],
        "frames_where_manifest_differs": bad["manifest"] if manifest is not None else "not checked",
        "npz_frames_compared": npz_checked,
        "frames_where_cache_npz_sha256_differs": bad["npz_sha256"] if inventory is not None else "not checked"}
    if a.original_metadata:
        orig = yaml.safe_load(open(a.original_metadata))["rosbag2_bagfile_information"]
        entry = next(t for t in orig["topics_with_message_count"] if t["topic_metadata"]["name"] == "/iv_points")
        report["topic_metadata_equals_original"] = entry["topic_metadata"] == meta["topics_with_message_count"][0][
            "topic_metadata"]
        report["original_version_and_storage"] = [orig["version"], orig["storage_identifier"]]
    json.dump(report, open(a.out, "w"), indent=1)
    print(json.dumps(report, indent=1))
    ok = (not any(bad[k] for k in bad) and report["metadata_matches_bag"]
          and report.get("topic_metadata_equals_original", True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
