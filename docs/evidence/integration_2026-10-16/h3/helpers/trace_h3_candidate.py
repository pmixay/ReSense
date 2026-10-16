#!/usr/bin/env python3
"""Read-only state trace for the one measured preexisting-candidate change in H3.

Replays ride piece 1 from its actual fresh-detector boundary; validates every captured
result against the measured candidate outside the registered timing telemetry.
"""
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np

from frame_diff import changes, normalize, write

RUN = "candidate-f8c088dc4f32-20261016T073403Z-4b64ec55"
REPO = Path("/evalworkspace") / RUN
sys.path[:0] = [str(REPO), str(REPO / "scripts")]
from resense import _native
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import frame_from_compact
from resense.tracking import Tracker
from scripts.cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps
import yaml


def plain(value):
    if dataclasses.is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def main():
    if not _native.enabled():
        raise ValueError("native backend required")
    run = Path("/evidence") / RUN
    analysis = Path("/evidence") / ("analysis-" + RUN)
    cfg = DetectorConfig.from_dict(yaml.safe_load((run / "gate_work/config.yaml").read_text())["resense"])
    files = list(np.array_split(np.array(cache_files("/data/cache/new_data")), 8)[1])
    stamps = load_cache_stamps("/data/cache/new_data")
    state = {"row": None, "events": []}
    original = Tracker._uncorroborated_spare

    def observed(self, cluster, history):
        before = dict(reason=cluster.reason, zone=cluster.zone, spared=cluster.spared,
                      prior_spare_hist=list(history), required_spares=self.cfg.column_free_min_spares)
        original(self, cluster, history)
        if cluster.spared:
            state["events"].append(dict(row=state["row"], before=before,
                after=dict(reason=cluster.reason, zone=cluster.zone, spared=cluster.spared)))

    Tracker._uncorroborated_spare = observed
    detector = Detector(cfg)
    trace, errors = [], []
    count = 0
    with (run / "frames/new_data_1.jsonl").open() as captured:
        for i, path in enumerate(files):
            state["row"] = i
            stem = cache_file_stem(path)
            frame = frame_from_compact(load_cache_array(path), cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
            result = detector.process(frame)
            measured = json.loads(next(captured))
            raw = {f.name: plain(getattr(result, f.name)) for f in dataclasses.fields(result) if f.name not in ("xyz", "corridor_idx")}
            raw["corridor_idx"] = dict(shape=list(result.corridor_idx.shape), dtype=str(result.corridor_idx.dtype), sha256=hashlib.sha256(result.corridor_idx.tobytes()).hexdigest())
            for name, current in (("serialized", result.to_dict()), ("raw", raw)):
                old, _ = normalize(measured[name])
                new, _ = normalize(current)
                for p, a, b in changes(old, new, name):
                    errors.append(dict(row=i, frame_id=stem, field=p, measured=a, replay=b))
            count += 1
            if any(c.spared for c in result.candidates) or 1351 <= i <= 1357:
                candidate_rows = []
                for ci, cl in enumerate(result.candidates):
                    if cl.spared or ci == 8:
                        tracks = []
                        for t in detector.tracker.tracks:
                            if t.last is cl:
                                tracks.append(dict(id=t.id, hits=t.hits, misses=t.misses,
                                    column_hist=list(t.column_hist), column_hold=t.column_hold, column_held=t.column_held,
                                    spare_hist=list(t.spare_hist), zone_hist=list(t.zone_hist),
                                    zone=t.zone, rule_zone=t.rule_zone, vote_zone=t.vote_zone,
                                    reported=t.reported, seen_reported=t.seen_reported,
                                    confidence=t.confidence, explained_hist=list(t.explained_hist), clean_run=t.clean_run))
                        candidate_rows.append(dict(index=ci, candidate=plain(cl), matched_tracks=tracks))
                serialized, _ = normalize(result.to_dict())
                trace.append(dict(row=i, frame_id=stem, obstacle=result.obstacle, warning=result.warning,
                    nearest=result.nearest_distance, clear=result.clear_distance,
                    detections=serialized["detections"], warnings=serialized["warnings"],
                    health=serialized["health"], candidates=candidate_rows))
        if next(captured, None) is not None:
            raise ValueError("replay omitted measured frames")
    report = dict(measured_commit="f8c088dc4f3243fbd15a3aae9be0459e8a0aa941", piece="new_data_1", frames=count,
        comparison_scope="Every raw and serialized captured result field outside the same registered timing normalization; fresh detector from the original eight-piece boundary, original stamps and native backend.",
        replay_matches_measured_candidate=not errors, mismatches=errors,
        spare_observations=state["events"], trace=trace)
    write(analysis / "candidate_promotion_trace.json", report)
    print(json.dumps(dict(frames=count, replay_matches_measured_candidate=not errors, mismatches=len(errors), spare_observations=state["events"]), indent=2))
    return 0 if not errors and count == 1409 else 1


if __name__ == "__main__":
    raise SystemExit(main())
