"""Decode and characterize every verified Falcon frame; retain a float32 node cache."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(variable, "1")

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
DATA = Path("/home/resense/data")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ros2_ws/src/resense_ros"))


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            checksum.update(block)
    return checksum.hexdigest()


def main():
    import numpy as np

    from resense.pointcloud import pointcloud2_to_structured
    from resense_ros import fastcloud

    receipt = json.loads((EVIDENCE / "source_receipt.json").read_text())
    if not receipt["verified"]:
        raise ValueError("source archive must be verified first")
    bag = DATA / "raw/falcon_test_second_dark/falcon_test_second_dark_0.db3"
    out = DATA / "decoded/falcon_test_second_dark"
    out.mkdir(parents=True, exist_ok=False)
    connection = sqlite3.connect(f"file:{bag}?mode=ro", uri=True)
    topics = {
        i: name
        for i, name, kind in connection.execute("SELECT id,name,type FROM topics")
        if kind == "sensor_msgs/msg/PointCloud2"
    }
    assert len(topics) == 1
    topic_id, topic = next(iter(topics.items()))
    count = connection.execute(
        "SELECT count(*) FROM messages WHERE topic_id=?", (topic_id,)
    ).fetchone()[0]
    if count != 4443:
        raise ValueError(f"expected 4443 frames, found {count}")
    started = time.monotonic()
    metadata, inventory, schema = [], [], None
    with (EVIDENCE / "frame_characterization.jsonl").open("w") as characterization:
        for index, (stamp_ns, raw) in enumerate(
            connection.execute(
                "SELECT timestamp,data FROM messages WHERE topic_id=? ORDER BY timestamp,id",
                (topic_id,),
            )
        ):
            message = fastcloud.parse_pointcloud2(raw)
            xyz, intensity, ring, n_raw, n_near = fastcloud.decode(
                fastcloud.packed(message), 2.5, 250.0
            )
            stamp = message.header.stamp.sec + message.header.stamp.nanosec * 1e-9
            path = out / f"f_{index:05d}.npz"
            np.savez_compressed(path, xyz=xyz, inten=intensity, ring=ring)
            # Open each written cache through its public reader: zip CRC and array shapes are checked.
            with np.load(path) as checked:
                assert (
                    checked["xyz"].shape == xyz.shape
                    and checked["inten"].shape == intensity.shape
                )
                assert (
                    checked["ring"].shape == ring.shape
                    and checked["xyz"].dtype == np.float32
                )
            metadata.append(
                {
                    "i": index,
                    "stamp": stamp,
                    "bag_t": stamp_ns / 1e9,
                    "frame_id": message.header.frame_id,
                    "topic": topic,
                    "has_ring": fastcloud.has_field(message, "ring"),
                    "n_raw": n_raw,
                    "n_near": n_near,
                }
            )
            inventory.append(
                {"frame": index, "bytes": path.stat().st_size, "sha256": digest(path)}
            )
            arr = pointcloud2_to_structured(message)
            points = np.column_stack([arr[axis] for axis in ("x", "y", "z")])
            distance = np.linalg.norm(points, axis=1)
            finite = np.isfinite(points).all(axis=1) & (distance > 0.05)
            azimuth = np.degrees(np.arctan2(points[:, 1], points[:, 0]))
            elevation = np.degrees(
                np.arctan2(points[:, 2], np.linalg.norm(points[:, :2], axis=1))
            )
            row = {
                "frame": index,
                "stamp": stamp,
                "raw_slots": len(points),
                "finite_returns": int(finite.sum()),
                "node_returns": len(xyz),
                "n_near": n_near,
                "range_quantiles_m": np.percentile(
                    distance[finite], [0, 50, 95, 99, 100]
                ).tolist(),
                "range_counts_gt_m": {
                    str(value): int(np.sum(finite & (distance > value)))
                    for value in (60, 100, 150, 200, 250, 327, 400)
                },
                "azimuth_bounds_deg": [
                    float(azimuth[finite].min()),
                    float(azimuth[finite].max()),
                ],
                "elevation_bounds_deg": [
                    float(elevation[finite].min()),
                    float(elevation[finite].max()),
                ],
                "intensity_quantiles": np.percentile(
                    arr["intensity"][finite], [0, 50, 99, 100]
                ).tolist(),
                "point_stamp_span_s": float(np.ptp(arr["timestamp"])),
                "scan_id_bounds": [
                    int(arr["scan_id"].min()),
                    int(arr["scan_id"].max()),
                ],
                "second_return_flags": int(np.count_nonzero(arr["is_2nd_return"])),
            }
            characterization.write(json.dumps(row, allow_nan=False) + "\n")
            if schema is None:
                schema = {
                    "topic": topic,
                    "frame_id": message.header.frame_id,
                    "point_step": message.point_step,
                    "height": message.height,
                    "fields": [
                        {
                            "name": f.name,
                            "offset": f.offset,
                            "datatype": f.datatype,
                            "count": f.count,
                        }
                        for f in message.fields
                    ],
                    "ring_semantics": "absent; detector receives None",
                }
                (DATA / "n2/falcon_first_frame.cdr").write_bytes(raw)
            if index % 100 == 0:
                print(
                    f"decoded {index + 1}/{count}; {time.monotonic() - started:.1f}s",
                    flush=True,
                )
    connection.close()
    if len(metadata) != 4443 or not all(
        b["stamp"] > a["stamp"] for a, b in zip(metadata, metadata[1:])
    ):
        raise ValueError("frame completeness or chronology failed")
    (out / "meta.json").write_text(json.dumps(metadata) + "\n")
    (EVIDENCE / "cache_inventory.json").write_text(
        json.dumps(inventory, indent=2) + "\n"
    )
    report = {
        "frames": len(metadata),
        "schema": schema,
        "cache": str(out),
        "float_cache": True,
        "range_filter_m": [2.5, 250.0],
        "raw_range_characterization_before_crop": True,
        "all_cache_files_crc_and_shapes_checked": True,
        "cache_bytes": sum(r["bytes"] for r in inventory),
        "cache_inventory_sha256": digest(EVIDENCE / "cache_inventory.json"),
        "cache_meta_sha256": digest(out / "meta.json"),
        "source_archive_sha256": receipt["sha256"],
        "elapsed_s": time.monotonic() - started,
        "decoder_sha256": digest(Path(fastcloud.__file__)),
    }
    (EVIDENCE / "cache_receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
