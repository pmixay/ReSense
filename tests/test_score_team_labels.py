"""Team evidence keeps missing coverage, ambiguous gauge and matching uncertainty visible."""
from itertools import product

import pytest

from scripts.score_team_labels import match_bounds, score


def target(name="box", relation="inside", distance=40.0, lateral=0.0, **kwargs):
    return {"name": name, "distance": distance,
            "bbox": [[distance, lateral - 0.2, -1.0], [distance + 0.4, lateral + 0.2, 0.0]],
            "n_points": 8, "gauge_relation": relation,
            "in_gauge": True if relation == "inside" else False if relation == "outside" else None, **kwargs}


def evidence(frames, **meta):
    return {"_meta": {"total_frames": len(frames), "coordinate_frame": "sensor_axis_mapped",
                      "sensor_to_vehicle_identity": True, "reviewed_all_frames": True, **meta},
            **{f"{i:05d}": values for i, values in enumerate(frames)}}


def result(index=0, *, detection=True, distance=40.0, lateral=0.0, z=-0.5, decision=None):
    return {"i": index, "decision": decision or ("STOP" if detection else "GO"),
            "obstacle": detection, "warning": False,
            "dets": ([{"d": distance, "c": [distance + 0.2, lateral, z], "size": [0.4, 0.4, 1.0]}]
                     if detection else []), "warns": []}


def test_null_gauge_is_uncertain_not_false():
    report = score([result()], evidence([[target(relation="boundary_uncertain")]]))
    assert report["summary"]["true_stop_detections_bounds"] == [0, 1]
    assert report["summary"]["false_stop_detections_bounds"] == [0, 1]
    assert report["summary"]["certain_inside_recall_bounds"] is None
    assert report["objects"]["box"]["first_stop_m_certain_assignment"] == 40.0


def test_unmatched_alarm_is_unresolved_without_exhaustive_annotations():
    report = score([result()], evidence([[]]))
    assert report["summary"]["false_stop_detections_bounds"] == [0, 1]
    assert report["summary"]["unmatched_stop_detections"] == 1
    exhaustive = score([result()], evidence([[]], exhaustive_obstacles=True))
    assert exhaustive["summary"]["false_stop_detections_bounds"] == [1, 1]
    uncertain = score([result()], evidence([[]], exhaustive_obstacles=True, coverage_unknown_frames=[0]))
    assert uncertain["summary"]["false_stop_detections_bounds"] == [0, 1]


def test_outside_alarm_is_false_but_uncertain_nearby_assignment_remains_uncertain():
    report = score([result()], evidence([[target(relation="outside")]]))
    assert report["summary"]["false_stop_detections_bounds"] == [1, 1]
    competing = score([result()], evidence([[target(relation="outside"), target("other", relation="unknown")]]))
    assert competing["summary"]["false_stop_detections_bounds"] == [0, 1]
    assert competing["objects"]["box"]["stop_match_frames_bounds"] == [0, 1]
    assert competing["objects"]["other"]["stop_match_frames_bounds"] == [0, 1]


def test_one_detection_cannot_be_counted_as_two_true_positives():
    report = score([result()], evidence([[target(), target("other")]]))
    assert report["summary"]["true_stop_detections_bounds"] == [1, 1]
    assert report["summary"]["certain_inside_recall_bounds"] == [0.5, 0.5]
    assert report["objects"]["box"]["stop_match_frames_bounds"] == [0, 1]


def test_matching_uses_raw_bbox_not_track_lateral_and_rejects_vertical_mismatch():
    label = target(lateral=3.0, lateral_sensor=3.0)
    label["lateral"] = -100.0
    assert score([result(lateral=3.0)], evidence([[label]]))["summary"]["true_stop_detections_bounds"] == [1, 1]
    assert score([result(lateral=3.0, z=4.0)], evidence([[label]]))["summary"]["true_stop_detections_bounds"] == [0, 0]


def test_pointless_and_out_of_range_rows_do_not_enter_recall():
    report = score([result()], evidence([[target(n_points=0), target("far", distance=251.0)]]))
    assert report["summary"]["certain_inside_object_frames"] == 0
    assert report["excluded_object_frames"] == {"no_point_support": 1, "outside_range": 1}


def test_radial_near_filter_is_not_mistaken_for_forward_filter():
    report = score([result(distance=1.8)], evidence([[target(distance=1.8)]]))
    assert report["summary"]["certain_inside_object_frames"] == 1


def test_truncating_both_sides_cannot_claim_a_complete_known_recording():
    with pytest.raises(ValueError, match="complete known recording"):
        score([result()], evidence([[target()]], bag="synthetic_platform"))


@pytest.mark.parametrize("change", ["missing_frame", "duplicate_result", "shifted_result", "null_as_false",
                                   "no_transform", "distance_max", "nan_box", "duplicate_name"])
def test_malformed_or_partial_evidence_is_rejected(change):
    labels = evidence([[target()], []])
    rows = [result(), result(1, detection=False)]
    if change == "missing_frame":
        del labels["00001"]
    elif change == "duplicate_result":
        rows[1]["i"] = 0
    elif change == "shifted_result":
        rows[1]["i"] = 2
    elif change == "null_as_false":
        labels["00000"][0].update(gauge_relation="unknown", in_gauge=False)
    elif change == "no_transform":
        labels["_meta"]["sensor_to_vehicle_identity"] = False
    elif change == "distance_max":
        labels["00000"][0]["distance"] = 40.4
    elif change == "nan_box":
        labels["00000"][0]["bbox"][0][0] = float("nan")
    elif change == "duplicate_name":
        labels["00000"].append(target())
    with pytest.raises(ValueError):
        score(rows, labels)


def test_non_stop_proposal_does_not_count_as_stop_and_tied_ranges_do_not_fake_held():
    rows = [result(0, decision="CAUTION"), result(1)]
    report = score(rows, evidence([[target()], [target()]]))
    assert report["objects"]["box"]["stop_match_frames_bounds"] == [1, 1]
    assert report["objects"]["box"]["stop_held_from_m_certain_assignment"] is None


def test_graph_bounds_equal_exhaustive_assignments_for_all_three_by_three_graphs():
    # Independent enumeration validates the matching-bound identity, including collisions
    # where choosing the nearest first would steal another target's only match.
    for mask in range(1 << 9):
        graph = [[j for j in range(3) if mask & (1 << (i * 3 + j))] for i in range(3)]
        assignments = []
        for assignment in product(range(-1, 3), repeat=3):
            used = [d for d in assignment if d >= 0]
            if len(used) == len(set(used)) and all(d < 0 or d in graph[i] for i, d in enumerate(assignment)):
                assignments.append(assignment)
        maximum = max(sum(d >= 0 for d in a) for a in assignments)
        maximal = [a for a in assignments if sum(d >= 0 for d in a) == maximum]
        for selected in ([], [0], [0, 2], [0, 1, 2]):
            counts = [sum(a[i] >= 0 for i in selected) for a in maximal]
            assert match_bounds(graph, selected) == [min(counts), max(counts)]
