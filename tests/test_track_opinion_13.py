"""Track opinion 1.3 (card G2, 21.10; docs/evidence/track_opinion_2026-10-21/PROTOCOL.md §6).

``tracking.doubt_falcon`` (true = v1.2.0): false turns the learned opinion off in the Falcon sensor
profiles, whose tracks the model has never been trained on; Pandar and manual profiles keep it. The
retrained model ships as a new file next to the 27.09 one, which stays loadable and scores as before.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

from resense.config import DetectorConfig, TrackingConfig
from resense.opinion import FEATURES, TrackOpinion, load_opinion
from resense.tracking import Tracker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ros2_ws/src/resense_ros"))
from resense_ros.sensor_profiles import apply_sensor_profile  # noqa: E402

MODELS = ROOT / "resense/models"
NEW = MODELS / "track_opinion_1.3.json"
NEW_REPORT = MODELS / "track_opinion_1.3_report.json"
# the 27.09 model's 19 columns (resense/models/track_opinion_report.json)
OLD_FEATURES = ["distance", "abs_lateral", "is_low", "frac_low", "hits", "lat_std", "lat_jump", "cz_std",
                "hmax_mean", "hmin_mean", "len_mean", "width_mean", "height_mean", "gauge_frac",
                "frac_demoted", "frac_column", "frac_beyond", "dist_rough", "hit_fraction"]
# features that read the injector's reflectivity or raw point budget, never a model input (EXPERIMENTS 22.09 §8)
FORBIDDEN = {"intensity", "log_n_mean", "vis_mean", "log_gauge"}


def _yaml_cfgs():
    return (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
            DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml")))


def test_doubt_falcon_default_equal_in_class_and_both_yaml():
    vals = {(c.tracking.doubt_falcon, c.tracking.doubt_model, c.tracking.doubt_threshold) for c in _yaml_cfgs()}
    assert len(vals) == 1
    assert TrackingConfig().doubt_falcon in (True, False)


@pytest.mark.parametrize("profile", ["falcon_ros", "falcon_native"])
def test_falcon_profiles_turn_the_opinion_off_when_asked(profile):
    cfg = DetectorConfig()
    cfg.tracking.doubt_falcon = False
    resolved, model = apply_sensor_profile(cfg, profile)
    assert model == "falcon_prime"
    assert resolved.tracking.doubt_model == "" and resolved.tracking.doubt_extra_hits == 0
    assert Tracker(resolved.tracking).opinion is None
    assert cfg.tracking.doubt_model != ""                     # the caller's config is not touched


@pytest.mark.parametrize("profile", ["falcon_ros", "falcon_native"])
def test_falcon_profiles_keep_the_opinion_at_v120_setting(profile):
    cfg = DetectorConfig()
    cfg.tracking.doubt_falcon = True
    resolved, _ = apply_sensor_profile(cfg, profile)
    assert resolved.tracking.doubt_model == cfg.tracking.doubt_model
    assert resolved.tracking.doubt_extra_hits == cfg.tracking.doubt_extra_hits


@pytest.mark.parametrize("profile", ["pandar128", "manual"])
@pytest.mark.parametrize("flag", [True, False])
def test_pandar_and_manual_profiles_never_change_the_opinion(profile, flag):
    cfg = DetectorConfig()
    cfg.tracking.doubt_falcon = flag
    resolved, _ = apply_sensor_profile(cfg, profile)
    assert resolved.tracking.doubt_model == cfg.tracking.doubt_model
    assert resolved.tracking.doubt_extra_hits == cfg.tracking.doubt_extra_hits


def test_the_2709_model_is_kept_and_reads_its_columns_by_name():
    old = load_opinion("track_opinion.json")
    assert old.features == OLD_FEATURES
    rng = np.random.default_rng(0)
    vals = rng.uniform(0.0, 2.0, size=(8, len(OLD_FEATURES)))
    vals[:, 0] = np.linspace(26.0, 200.0, 8)
    got = []
    for v in vals:
        x = np.zeros(len(FEATURES))
        for f, a in zip(OLD_FEATURES, v):
            x[FEATURES.index(f)] = a
        got.append(old.prob(x))
    # the scores of the shipped model on these vectors at v1.2.0 (before any feature was appended)
    ref = [0.142477548906, 0.417070224294, 0.359893928943, 0.192620422005, 0.02744698833, 0.051110594885,
           0.05872134176, 0.093814511522]
    assert np.allclose(got, ref, rtol=0, atol=1e-11)


def _new_spec():
    if not NEW.exists():
        pytest.skip("track_opinion_1.3.json not trained yet (PROTOCOL §2)")
    return json.loads(NEW.read_text())


def test_new_model_uses_only_known_features_and_no_injector_artefact():
    spec = _new_spec()
    op = TrackOpinion(spec)
    assert set(op.features) <= set(FEATURES)
    assert not set(op.features) & FORBIDDEN
    assert len(spec["trees"]) <= 200 and all(len(t["feature"]) <= 63 for t in spec["trees"])


def test_new_model_report_records_export_identity_and_groups():
    _new_spec()
    rep = json.loads(NEW_REPORT.read_text())
    assert rep["export_max_abs_diff"] < 1e-9
    assert rep["features"] == TrackOpinion(json.loads(NEW.read_text())).features
    assert rep["heldout"]["delayed_sequences_at_threshold"] == 0
    assert not any("heldout_2026-10-15" in str(g) for g in rep["groups"])
