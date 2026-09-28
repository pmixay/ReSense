"""Audit guards for the source-bound four-config positive observer."""
import pytest

from scripts.compare_raw_positive_configs import compare, unmatched_pairs, validate_alignment


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
