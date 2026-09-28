"""Audit guards for the source-bound four-config positive observer."""
import pytest

from scripts.compare_raw_positive_configs import (
    compare, node_raw_frames, sha, unmatched_pairs, validate_alignment, validate_native,
)


def row(frame, *, stamp=None, matches=(), detections=()):
    return {"frame": frame, "stamp": frame * .1 if stamp is None else stamp,
            "frame_id": "lidar", "label_matches": [{"label": name} for name in matches],
            "detections": list(detections), "unmatched_detection_indices": list(range(len(detections)))}


def test_alignment_rejects_same_incomplete_split_and_timestamp_changes():
    with pytest.raises(ValueError, match="incomplete"):
        validate_alignment({"a": [row(0)], "b": [row(0)]}, 2)
    with pytest.raises(ValueError, match="identities differ"):
        validate_alignment({"a": [row(0), row(1)], "b": [row(0), row(1, stamp=.2)]}, 2)
    assert len(validate_alignment({"a": [row(0), row(1)], "b": [row(0), row(1)]}, 2)) == 2


def test_physical_matching_is_one_to_one_and_ignores_track_id_renumbering():
    det = {"distance": 20., "lateral": .2, "kind": "low", "id": 1}
    duplicate = dict(det, id=9)
    assert unmatched_pairs([det], [duplicate]) == {0: 0}
    assert len(unmatched_pairs([det], [det, duplicate])) == 1
    assert unmatched_pairs([det], [dict(det, distance=30.)]) == {}


def test_pair_reports_lost_target_despite_equal_aggregate_count():
    result = compare([row(0, matches=["person"])], [row(0, matches=["rail"])])
    assert result["lost_label_frames"] == result["gained_label_frames"] == 1
    assert not result["passed_frame_recall_and_no_new_unmatched"]


def test_native_guard_rejects_inactive_wrong_hash_or_external_binary(tmp_path):
    native = tmp_path / "resense" / "native.so"
    native.parent.mkdir()
    native.write_bytes(b"native fixture")
    expected = sha(native)
    assert validate_native(native, "native (native.so)", expected, tmp_path) == native
    with pytest.raises(ValueError, match="not active"):
        validate_native(native, "numpy (RESENSE_NATIVE=0)", expected, tmp_path)
    with pytest.raises(ValueError, match="origin/hash"):
        validate_native(native, "native (native.so)", "wrong", tmp_path)
    with pytest.raises(ValueError, match="origin/hash"):
        validate_native(native, "native (native.so)", expected, tmp_path / "other")


def test_raw_reader_preserves_header_clock_when_receive_intervals_diverge(tmp_path, monkeypatch):
    """A real two-message bag makes receive-time substitution observably wrong."""
    from pathlib import Path
    import numpy as np
    from rosbags.rosbag2 import Writer
    from rosbags.typesys import Stores, get_typestore
    from resense.config import DetectorConfig
    from resense.frame import axis_matrix
    from resense.io import iter_bag_frames

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    ts = get_typestore(Stores.ROS2_HUMBLE)
    PointField = ts.types["sensor_msgs/msg/PointField"]
    PointCloud = ts.types["sensor_msgs/msg/PointCloud2"]
    Header = ts.types["std_msgs/msg/Header"]
    Time = ts.types["builtin_interfaces/msg/Time"]
    arr = np.array([(12.345, 1.234, -0.567, 17.25, 127)],
                   dtype=[("x", "<f4"), ("y", "<f4"), ("z", "<f4"),
                          ("intensity", "<f4"), ("ring", "<u2")])
    fields = [PointField(name, offset, kind, 1) for name, offset, kind in (
        ("x", 0, 7), ("y", 4, 7), ("z", 8, 7), ("intensity", 12, 7), ("ring", 16, 4))]
    topic = "/lidar"
    bag = tmp_path / "clock_divergence"
    with Writer(bag, version=9) as writer:
        connection = writer.add_connection(topic, "sensor_msgs/msg/PointCloud2", typestore=ts)
        for ns, received in ((0, 200_000_000_000), (100_000_000, 200_700_000_000)):
            msg = PointCloud(Header(Time(100, ns), "source_lidar"), 1, 1, fields, False,
                             arr.itemsize, arr.itemsize, np.frombuffer(arr.tobytes(), dtype=np.uint8), True)
            writer.write(connection, received, ts.serialize_cdr(msg, "sensor_msgs/msg/PointCloud2"))
    cfg = DetectorConfig()
    frames = list(node_raw_frames(bag, cfg, topic))
    receive_frames = list(iter_bag_frames(str(bag), cfg.sensor, topic=topic))
    assert [frame.stamp for _, frame in receive_frames] == [200., 200.7]
    assert [frame.stamp for _, frame in frames] == [100., 100.1]
    assert [i for i, _ in frames] == [0, 1]
    assert [frame.frame_id for _, frame in frames] == ["source_lidar"] * 2
    expected_xyz = np.array([[12.345, 1.234, -0.567]], np.float32) @ axis_matrix(cfg.sensor).astype(np.float32).T
    np.testing.assert_array_equal(frames[0][1].xyz, expected_xyz)
    np.testing.assert_array_equal(frames[0][1].ring, [127])
    np.testing.assert_array_equal(frames[0][1].intensity, [17.25])
