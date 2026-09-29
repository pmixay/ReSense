"""The tunable detector parameters (GET /api/presets/schema) and preset configs."""
from __future__ import annotations

import json
import re

import pytest

from resense.config import DetectorConfig
from resense_web import params

CYRILLIC = re.compile("[а-яА-ЯёЁ]")


def _default_cfg() -> DetectorConfig:
    return DetectorConfig.from_yaml(str(params.DEFAULT_CONFIG_PATH))


def test_specs_shape_and_defaults_from_config_file():
    specs = params.PARAM_SPECS
    assert 12 <= len(specs) <= 20
    assert len({s["key"] for s in specs}) == len(specs)
    cfg = _default_cfg()
    for s in specs:
        assert s["type"] in ("float", "int", "bool")
        for k in ("group", "label", "help"):
            assert CYRILLIC.search(s[k]), (s["key"], k)
        section, name = s["key"].split(".")
        value = getattr(getattr(cfg, section), name)
        assert not isinstance(value, (list, tuple, dict, str)), s["key"]      # scalars only
        if s["type"] == "bool":
            assert s["default"] is value and "min" not in s
            continue
        py = float if s["type"] == "float" else int
        assert type(s["default"]) is py and s["default"] == value, s["key"]
        assert s["min"] <= s["default"] <= s["max"] and s["step"] > 0, s["key"]
        assert all(type(s[k]) in (int, float) for k in ("min", "max", "step"))
    json.dumps(specs, ensure_ascii=False)


def test_texts_use_the_ui_decision_names():
    """Labels and help texts are plain Russian: decisions as the UI names them (СТОП, ВНИМАНИЕ,
    ОШИБКА, СВОБОДНО), not the topic values GO / CAUTION / STOP / FAULT."""
    latin = re.compile(r"\b(GO|CAUTION|STOP|FAULT)\b")
    for s in params.PARAM_SPECS:
        for k in ("group", "label", "help"):
            assert not latin.search(s[k]), (s["key"], k, s[k])
        assert s["help"].rstrip().endswith((".", ")")), s["key"]
    helps = " ".join(s["help"] for s in params.PARAM_SPECS)
    assert "СТОП" in helps and "ВНИМАНИЕ" in helps and "ОШИБКА" in helps


def test_every_key_accepted_by_from_dict():
    for s in params.PARAM_SPECS:
        section, name = s["key"].split(".")
        DetectorConfig.from_dict({section: {name: s["default"]}})


def test_validate_converts_types():
    out = params.validate_overrides({"tracking.confirm_time_s": 1, "cluster.min_points": 7.0,
                                     "lowobj.enabled": False, "cluster.eps": "0,4",
                                     "health.min_points": "15000"})
    assert out == {"cluster.eps": 0.4, "cluster.min_points": 7, "tracking.confirm_time_s": 1.0,
                   "lowobj.enabled": False, "health.min_points": 15000}
    assert type(out["tracking.confirm_time_s"]) is float and type(out["cluster.min_points"]) is int
    assert list(out) == [k for k in params.PARAM_KEYS if k in out]      # the schema's order
    assert params.validate_overrides({}) == {} and params.validate_overrides(None) == {}
    assert params.validate_overrides({"lowobj.enabled": "true"}) == {"lowobj.enabled": True}


@pytest.mark.parametrize("bad", [
    {"cluster.nonexistent": 1},
    {"tracking.frame_dt": 0.2},                 # a real field, but not a tunable one
    {"cluster.min_points": 5.5},
    {"cluster.min_points": 1},
    {"cluster.eps": 5},
    {"cluster.eps": True},
    {"cluster.eps": None},
    {"cluster.eps": "abc"},
    {"cluster.eps": float("nan")},
    {"lowobj.enabled": 1},
    {"lowobj.enabled": "maybe"},
    {"gauge.profile": [[0, 0]]},
])
def test_validate_rejects(bad):
    with pytest.raises(ValueError) as e:
        params.validate_overrides(bad)
    assert CYRILLIC.search(str(e.value))


def test_validate_rejects_non_dict():
    with pytest.raises(ValueError):
        params.validate_overrides([("cluster.eps", 0.3)])


def test_build_config_applies_overrides_only():
    base = _default_cfg()
    assert params.build_config({}) == base
    cfg = params.build_config({"tracking.confirm_time_s": 0.8, "gauge.warning_margin": 0.5,
                               "lowobj.enabled": False})
    assert cfg.tracking.confirm_time_s == 0.8 and cfg.tracking.frames_to_confirm() == 8
    assert cfg.gauge.warning_margin == 0.5 and cfg.lowobj.enabled is False
    cfg.tracking.confirm_time_s, cfg.gauge.warning_margin, cfg.lowobj.enabled = (
        base.tracking.confirm_time_s, base.gauge.warning_margin, base.lowobj.enabled)
    assert cfg == base
    with pytest.raises(ValueError):
        params.build_config({"cluster.eps": 9})


def test_snapshot_is_json_and_round_trips():
    snap = params.config_snapshot({"cluster.eps": 0.5})
    text = json.dumps(snap)
    cfg = DetectorConfig.from_dict(json.loads(text))
    assert cfg == params.build_config({"cluster.eps": 0.5})
    assert snap["cluster"]["eps"] == 0.5
    assert params.defaults()["cluster.eps"] == _default_cfg().cluster.eps


def test_fallback_without_config_file(monkeypatch, tmp_path):
    monkeypatch.setattr(params, "DEFAULT_CONFIG_PATH", tmp_path / "missing.yaml")
    params._base_dict.cache_clear()
    try:
        assert params.build_config({}) == DetectorConfig()
        assert params.build_config({"cluster.min_points": 9}).cluster.min_points == 9
    finally:
        params._base_dict.cache_clear()
