#!/usr/bin/env python3
"""Extract compact state witnesses for the H3 ride candidate promotion."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
analysis = root / "analysis-candidate-f8c088dc4f32-20261016T073403Z-4b64ec55"
data = json.loads((analysis / "candidate_promotion_trace.json").read_text())
assert data["replay_matches_measured_candidate"] and data["frames"] == 1409
target = next(row for row in data["trace"] if row["row"] == 1354)
candidate = next(row for row in target["candidates"] if row["index"] == 8)
observation = next(event for event in data["spare_observations"] if event["row"] == 1354)
result = dict(measured_commit=data["measured_commit"], frame_id=target["frame_id"], row=1354, candidate_index=8,
    obstacle=target["obstacle"], warning=target["warning"], nearest=target["nearest"], clear=target["clear"],
    detections=target["detections"], warnings=target["warnings"],
    candidate={k: v for k, v in candidate["candidate"].items() if k != "points_idx"},
    matched_tracks=candidate["matched_tracks"], spare_observation=observation,
    replay_validation=dict(frames=1409, raw_and_serialized_mismatches=0),
    source_paths=["resense/clustering.py:_corridor_cluster / _advisory_reason", "resense/tracking.py:_uncorroborated_spare / Track.column_held / Track.rule_zone"])
(analysis / "promotion_interpretation.json").write_bytes((json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
print(json.dumps(result, indent=2))
