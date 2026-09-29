"""Checks for the competitor-rule screen (scripts/screen_competitor_rules.py).

The synthetic tests build tiny detections, labels and events and need nothing. The two evidence tests read
the committed judgement outputs; they carry ``realdata`` so the Docker image, which does not ship
``docs/evidence/judgement_*``, deselects them.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("screen_competitor_rules", ROOT / "scripts" / "screen_competitor_rules.py")
assert _spec is not None and _spec.loader is not None
screen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(screen)

EVIDENCE = ROOT / "docs" / "evidence"
OFFLINE = EVIDENCE / "judgement_2026-09-28" / "raw" / "offline"
SCREEN_JSON = EVIDENCE / "results" / "competitor_rule_screen_2026-09-29.json"


def det(distance, n_points=20, dz=1.0, height_min=0.2, lateral=0.0):
    return {"distance": distance, "n_points": n_points, "size": [0.5, 0.5, dz], "height_min": height_min,
            "lateral": lateral, "id": 1}


def test_episodes_counts_runs_of_true():
    assert screen.episodes([]) == 0
    assert screen.episodes([False, False]) == 0
    assert screen.episodes([True, True, False, True, False, True, True]) == 3


def test_shape_rule_needs_far_sparse_and_flat():
    shape = screen.RULES["tunnelguard_shape"].veto
    beams = screen.BEAM_VERTICAL_RAD
    far = 100.0
    flat = 1.2 * beams * far - 0.01           # just below 1.2 beam spacings at 100 m
    assert shape(det(far, n_points=5, dz=flat))
    assert not shape(det(far, n_points=5, dz=1.2 * beams * far + 0.01))      # tall enough
    assert not shape(det(far, n_points=15, dz=flat))                         # well supported: exempt
    assert not shape(det(40.0, n_points=5, dz=0.0))                          # not beyond 40 m
    assert shape(det(40.5, n_points=5, dz=0.0))


def test_gravity_rule_needs_far_and_raised():
    gravity = screen.RULES["tunnelguard_gravity"].veto
    assert gravity(det(61.0, height_min=1.1))
    assert not gravity(det(60.0, height_min=1.1))
    assert not gravity(det(61.0, height_min=1.0))
    assert not gravity(det(100.0, height_min=0.3))


def _labels():
    rows = {"_meta": {"objects": {"box": {"in_gauge": True, "frames": [0, 3]}}}}
    for i in range(4):
        rows[f"{i:05d}"] = [{"name": "box", "plausible": True, "in_gauge": True, "bbox": [[50.0, -1, 0], [52.0, 1, 2]]}]
    return rows


def _frames(per_frame):
    return [{"frame": i, "detections": dets, "warnings": [], "obstacle": bool(dets)}
            for i, dets in enumerate(per_frame)]


def test_set_o_scores_matches_and_strays():
    frames = _frames([[], [det(51.0)], [det(51.0), det(90.0)], [det(56.0)]])     # 56 m is 4 m past the box: a stray
    out = screen.score_set_o(frames, _labels())
    assert out["objects"]["box"] == {"in_gauge": True, "stop_frames": 2, "first_stop_m": 51.0}
    assert out["stray_stop_detections"] == 2


def test_set_o_veto_removes_only_what_it_flags():
    # frame 0: a flat, sparse detection at 51 m (beyond 40 m: the shape rule vetoes it); frame 1: a solid one
    frames = _frames([[det(51.0, n_points=5, dz=0.0)], [det(51.0)]])
    base = screen.score_set_o(frames, _labels())
    assert screen.score_set_o(frames, _labels(), veto=lambda d: False) == base
    out = screen.score_set_o(frames, _labels(), veto=screen.RULES["tunnelguard_shape"].veto)
    assert base["objects"]["box"]["stop_frames"] == 2
    assert out["objects"]["box"]["stop_frames"] == 1
    far = _frames([[det(70.0, n_points=5, dz=0.0)]])
    labels = {"_meta": {"objects": {"box": {"in_gauge": True, "frames": [0, 0]}}},
              "00000": [{"name": "box", "plausible": True, "in_gauge": True, "bbox": [[69.0, -1, 0], [71.0, 1, 2]]}]}
    assert screen.score_set_o(far, labels)["objects"]["box"]["stop_frames"] == 1
    assert screen.score_set_o(far, labels, veto=screen.RULES["tunnelguard_shape"].veto)["objects"]["box"] == \
        {"in_gauge": True, "stop_frames": 0, "first_stop_m": None}


def test_screen_empty_counts_frames_episodes_and_vetoed_detections():
    bag = _frames([[det(50.0)], [det(50.0)], [], [det(70.0, n_points=5, dz=0.0)], []])
    plain = screen.screen_empty({"bag": bag}, None)
    assert plain == {"stop_frames": 3, "stop_episodes": 2, "detections": 3, "vetoed": 0}
    shaped = screen.screen_empty({"bag": bag}, screen.RULES["tunnelguard_shape"].veto)
    assert shaped == {"stop_frames": 2, "stop_episodes": 1, "detections": 3, "vetoed": 1}


def test_screen_real_reports_first_stop_frame():
    rows = _frames([[], [], [det(56.0)], [det(56.0)]])
    assert screen.screen_real(rows, None) == {"stop_frames": 2, "first_stop_frame": 2}
    assert screen.screen_real(_frames([[], []]), None) == {"stop_frames": 0, "first_stop_frame": None}


def test_ride_events_disappear_only_when_every_record_is_vetoed():
    veto = screen.RULES["tunnelguard_gravity"].veto
    raised = {"candidate_detection": det(100.0, height_min=1.5)}
    grounded = {"candidate_detection": det(100.0, height_min=0.2)}
    events = [{"candidate_stop_records": [raised, raised]},
              {"candidate_stop_records": [raised, grounded]},
              {"candidate_stop_records": [grounded]}]
    assert screen.screen_ride_events(events, veto) == {"events": 3, "records": 5, "events_removed": 1,
                                                       "records_removed": 3}


def test_promotion_counts_only_centred_advisories_of_the_named_reasons(tmp_path):
    def warn(reason, lateral, distance=51.0):
        return {"reason": reason, "lateral": lateral, "distance": distance}

    empty = [{"frame": 0, "detections": [], "warnings": [warn("beyond_axis", 0.1), warn("beyond_axis", 0.9),
                                                         warn("column", 0.0), warn("beyond_height_ref", -0.3)]}]
    set_o = [{"frame": i, "detections": [], "warnings": [warn("beyond_axis", 0.2, 51.0)]} for i in range(2)]
    out = screen.promotion_screen(tmp_path, _labels(), {"bag": empty}, set_o)
    assert out["empty_recordings_would_be_false_stops"] == {"beyond_axis": 1, "beyond_height_ref": 1}
    assert out["set_o_in_gauge_object_gains"] == {"beyond_axis": 2, "beyond_height_ref": 0}
    assert out["set_o_gain_range_m"] == {"beyond_axis": [51.0, 51.0], "beyond_height_ref": None}


@pytest.mark.realdata(str(OFFLINE))
def test_harness_reproduces_the_published_set_o_rows():
    labels = json.loads((ROOT / "labels" / "cloud_with_fake_obj.json").read_text(encoding="utf-8"))
    frames = screen.load_frames(EVIDENCE, screen.SET_O_BAG)
    screen.check_reproduces_published(EVIDENCE, labels, frames)         # raises SystemExit on any difference


@pytest.mark.realdata(str(OFFLINE))
def test_committed_screen_matches_a_fresh_run():
    fresh = screen.run(EVIDENCE, ROOT / "labels" / "cloud_with_fake_obj.json")
    assert json.loads(SCREEN_JSON.read_text(encoding="utf-8")) == fresh
