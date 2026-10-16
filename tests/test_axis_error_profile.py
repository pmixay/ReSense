"""Checks for scripts/axis_error_profile.py on a small synthetic label set (no organizer data)."""

import importlib.util
import json
from pathlib import Path

import pytest

# CI also runs from / inside the image; load the script by path, not the current directory.
_script = Path(__file__).resolve().parents[1] / "scripts" / "axis_error_profile.py"
_spec = importlib.util.spec_from_file_location("resense_axis_error_profile", _script)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def _labels():
    """One object closing in 2 m per frame from 100 m, lateral 0.5 m near; the far lateral is off by
    +0.4 m at 90-100 m and alternates +/-0.1 m in the 40-60 m bin."""
    labels = {"_meta": {"bag": "synthetic"}}
    for frame, distance in enumerate(range(100, 0, -2)):
        if distance >= 90:
            lateral = 0.9
        elif 40 <= distance < 60:
            lateral = 0.5 + (0.1 if frame % 2 else -0.1)
        else:
            lateral = 0.5
        labels[f"{frame:05d}"] = [{"name": "box", "distance": float(distance), "lateral": lateral,
                                   "n_points": max(1, 2000 // distance)}]
    return labels


def test_axis_error_and_jitter_by_range():
    tracks = _module.load_tracks(_labels())
    assert list(tracks) == ["box"]
    bins = ((90.0, 101.0), (40.0, 60.0), (8.0, 25.0))
    axis = _module.axis_error_by_range(tracks, bins=bins)
    assert axis[(90.0, 101.0)]["median"] == pytest.approx(0.4)
    assert axis[(40.0, 60.0)]["max"] == pytest.approx(0.1)
    assert axis[(8.0, 25.0)]["max"] == pytest.approx(0.0)
    jitter = _module.jitter_by_range(tracks, bins=bins)
    assert jitter[(40.0, 60.0)]["median"] == pytest.approx(0.2)
    assert jitter[(8.0, 25.0)]["max"] == pytest.approx(0.0)


def test_object_without_near_frames_is_skipped():
    labels = {"_meta": {}, "00000": [{"name": "far", "distance": 200.0, "lateral": 3.0, "n_points": 1}],
              "00001": [{"name": "far", "distance": 198.0, "lateral": 3.0, "n_points": 1}]}
    axis = _module.axis_error_by_range(_module.load_tracks(labels))
    assert all(v == {"n": 0} for v in axis.values())


def test_points_by_range_and_cli(tmp_path, capsys):
    labels_path = tmp_path / "labels.json"
    labels_path.write_text(json.dumps(_labels()), encoding="utf-8")
    points = _module.points_by_range(_module.load_tracks(_labels()), bins=((90.0, 101.0), (8.0, 25.0)))
    assert points["box"][(90.0, 101.0)] < points["box"][(8.0, 25.0)]
    out_json = tmp_path / "out.json"
    assert _module.main(["--labels", str(labels_path), "--json", str(out_json)]) == 0
    printed = capsys.readouterr().out
    assert "axis error median" in printed and "| box |" in printed
    assert "axis_error" in json.loads(out_json.read_text(encoding="utf-8"))
