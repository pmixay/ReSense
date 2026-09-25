"""Helpers of the train-speed evaluation (scripts/eval_real.py): stamps snapped to the rotation
and the per-frame reference speed of scripts/speed_reference.py."""
import importlib.util
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "eval_real.py"
SPEC = importlib.util.spec_from_file_location("resense_eval_real", PATH)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_nominal_stamps_snap_every_gap_to_whole_rotations():
    recv = {"b_0000": 10.0, "b_0001": 10.082, "b_0002": 10.215, "b_0003": 10.301, "b_0004": 10.52}
    out = module.nominal_stamps(recv)
    gaps = [round(out[b] - out[a], 6) for a, b in zip(sorted(out), sorted(out)[1:])]
    assert out["b_0000"] == 10.0
    assert gaps == [0.1, 0.1, 0.1, 0.2]           # jitter removed, the dropped frame kept
    assert module.nominal_stamps({}) == {}


def test_nominal_stamps_never_collapse_a_short_gap():
    out = module.nominal_stamps({"a_0": 0.0, "a_1": 0.04, "a_2": 0.2})
    assert out["a_1"] - out["a_0"] == 0.1 and out["a_2"] > out["a_1"]


def test_reference_speeds_interpolate_invalid_frames(tmp_path):
    rows = [{"frame": 0}, {"frame": 1, "ref_ok": True, "ref_speed": 10.0},
            {"frame": 2, "ref_ok": False, "ref_speed": 99.0}, {"frame": 3, "ref_ok": True, "ref_speed": 12.0},
            {"frame": 4}]
    p = tmp_path / "bag.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows))
    v = module.reference_speeds(str(p), 5)
    assert v[0] is None and v[4] is None          # outside the valid span: unknown
    assert abs(v[1] - 11.0) < 1e-9 and abs(v[3] - 11.0) < 1e-9   # 5-frame median of the two valid values
    assert abs(v[2] - 11.0) < 1e-9                # the invalid frame interpolated, not its 99 m/s
