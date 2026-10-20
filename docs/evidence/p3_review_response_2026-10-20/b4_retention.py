"""Measure B4 persistence through the existing ten-second keep cap."""
from copy import deepcopy
import json
import math
from pathlib import Path

import run_checks
from resense.config import DetectorConfig
from resense.tracking import Tracker

HERE = Path(__file__).resolve().parent


def number(value):
    return value if math.isfinite(value) else str(value)


def run(warm, error, gauge_voxels=12, keep=True, traced=False):
    cfg = DetectorConfig().tracking
    cfg.stop_keep_signature = keep
    tracker = Tracker(cfg)
    _, clean = run_checks.b4_case(20., 0., (2.7, 3.))
    _, fault = run_checks.b4_case(20., error, (2.7, 3.))
    fault.n_gauge = gauge_voxels
    original = Tracker._keeps
    events = []

    def wrapped(self, track, cluster):
        result = original(self, track, cluster)
        events.append({'id': track.id, 'since_clean': number(track.since_clean), 'n_gauge': cluster.n_gauge,
                       'demoted': cluster.demoted, 'previous_reported': track.reported,
                       'previous_zone': track.zone, 'returned': bool(result)})
        return result

    if traced:
        Tracker._keeps = wrapped
    rows = []
    try:
        for k in range(warm + 130):
            start = len(events)
            tracker.update([deepcopy(clean if k < warm else fault)], frame_dt=.1)
            rows.append({'k': k, 'after_fault': k >= warm,
                         'STOP': any(track.zone == 'gauge' for track in tracker.confirmed()),
                         'state_hash': run_checks.fingerprint(tracker.tracks),
                         'tracks': [{'since_clean': number(t.since_clean), 'zone_hist': t.zone_hist,
                                     'kept': t.kept, 'zone': t.zone, 'reported': t.reported,
                                     'misses': t.misses, 'last_reason': t.last.reason} for t in tracker.tracks],
                         'actual_keep_calls': events[start:]})
    finally:
        Tracker._keeps = original
    return {'warm_scans': warm, 'error': error, 'gauge_voxels': gauge_voxels,
            'keep_enabled': keep, 'rows': rows}


def main():
    failed = HERE / 'b4_retention.json'
    if failed.exists():
        destination = run_checks.WORK / 'b4_retention_partial.json.txt'
        assert not destination.exists()
        failed.rename(destination)
    cases = []
    for args in [(0, 1.6, 12, True), (12, 0., 12, True), (12, 1.6, 12, True),
                 (12, 1.6, 9, True), (12, 1.6, 12, False)]:
        plain = run(*args, traced=False)
        traced = run(*args, traced=True)
        for a, b in zip(plain['rows'], traced['rows'], strict=True):
            assert {k: v for k, v in a.items() if k != 'actual_keep_calls'} == {
                k: v for k, v in b.items() if k != 'actual_keep_calls'}
        traced['plain_row_hashes'] = [row['state_hash'] for row in plain['rows']]
        cases.append(traced)
    run_checks.save(HERE / 'b4_retention.json', cases)
    for case in cases:
        hits = [row['k'] for row in case['rows'] if row['STOP'] and row['after_fault']]
        kept = [row['k'] for row in case['rows'] if any(call['returned'] for call in row['actual_keep_calls'])]
        print(json.dumps({'warm': case['warm_scans'], 'error': case['error'], 'n_gauge': case['gauge_voxels'],
                          'keep_enabled': case['keep_enabled'], 'post_fault_STOP_count': len(hits),
                          'last_STOP': max(hits) if hits else None, 'last_actual_keep': max(kept) if kept else None}))


if __name__ == '__main__':
    main()
