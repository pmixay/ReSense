"""Current-source synthetic reproducer: a missing bed fit releases a K2 reach cap.

This records a finding, not a passing acceptance test. No detector source is patched.
    PYTHONPATH=. python docs/evidence/k1_k2_review_2026-10-20/probe_missing_floor.py
"""
import json
from dataclasses import replace

import numpy as np
from resense import _native
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.gauge import gauge_core_mask
from resense.track import _fit_floor, estimate_track
from tests.test_k1_k2_axis import V5, _cfg, _cluster, _run
from tests.test_wall_drift import _entry_scene


def snapshot(track):
    return {"axis_valid": track.axis_valid, "joint_reach": track.joint_reach,
            "joint_used": track.joint_used, "base_axis_valid": track.base.axis_valid}


def main():
    cloud, _ = _entry_scene(j=1 / 60000, inner_to=70)
    rows = []
    for native in (False, True):
        if native and not _native.AVAILABLE:
            raise RuntimeError("native binary required for the second control")
        _native.set_enabled(native)
        for extension in (0.0, 15.0):
            cfg = _cfg(**dict(V5, axis_joint_reach_cap=True, axis_joint_reach_dual=extension))
            before = _run(cloud, cfg)[-1]
            # Retain many observed points, but none in the base model's bed-fitting band.
            lateral = cloud[:, 1] - before.base.center_y(cloud[:, 0])
            missing = cloud[np.abs(lateral) > cfg.floor_halfwidth + .1]
            assert len(missing) > 100
            assert _fit_floor(missing, cfg, before.base) is None
            after = estimate_track(missing, cfg, prev=before)
            same_base = estimate_track(missing, _cfg(), prev=before.base)
            assert same_base is before.base  # positive control: ordinary path holds its prior
            assert before.joint_reach > 0 and before.axis_valid < before.base.axis_valid
            assert after.axis_valid == before.base.axis_valid and after.joint_reach == 0
            # Decision-path consequence at the dual classifier: an identical out-of-base cluster
            # is demoted with the old cap but not after losing the bed. This is not an E2E STOP claim.
            det = Detector(replace(DetectorConfig(), track=cfg))
            x = before.joint_reach + 1
            y = float(before.center_y(x))
            zones = []
            for track in ((before, after) if extension > 0 else ()):
                det.track = track
                candidate = _cluster(x, x + .4, y - .1, y + .1)
                assert gauge_core_mask(
                    np.array([candidate.centroid[1] - float(track.center_y(candidate.centroid[0]))]),
                    np.array([.9]), np.array([candidate.centroid[0]]), det.cfg.gauge,
                )[0]
                det._dual_zone([candidate])
                zones.append([candidate.zone, candidate.reason])
            assert zones == ([["warning", "beyond_axis"], ["gauge", ""]] if extension > 0 else [])
            rows.append({"native": native, "extension_m": extension, "points_without_floor": len(missing),
                         "before": snapshot(before), "after": snapshot(after),
                         "direct_dual_classifier_before_after": zones})
    print(json.dumps({"scope": "synthetic track-estimator and direct classifier probe; recording exposure unmeasured",
                      "finding_reproduced": True, "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
