"""Executed reference-quality gates, including a measured nonzero positive control."""
from collections import Counter
import json
import argparse

import numpy as np
import open3d as o3d

from direct_reference import align, cloud
from reference import CACHES, HERE, raw_cloud


def verdict(row):
    if row['projected_disagreement_m'] > .1:
        return 'initializations_disagree'
    if row['reverse_translation_m'] > .1:
        return 'reverse_translation'
    if row['reverse_rotation_deg'] > .05:
        return 'reverse_rotation'
    if min(row['primary']['fitness'], row['alternate_seed_result']['fitness'], row['reverse']['fitness']) < .7:
        return 'insufficient_overlap'
    return 'accepted'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--deskew', action='store_true')
    args = parser.parse_args()
    reference = json.loads((HERE / ('direct-reference-deskew.json' if args.deskew else 'direct-reference.json')).read_text())
    records = []
    for row in reference['rows']:
        if 'consistent' not in row:
            records.append(dict(sequence=row['sequence'], frame=row['frame'], station=row['station'],
                                executed_gate='no_near_rail_observation'))
            continue
        gate = verdict(row)
        assert (gate == 'accepted') == row['consistent']
        records.append(dict(sequence=row['sequence'], frame=row['frame'], station=row['station'],
                            executed_gate=gate))
    xyz, _ = raw_cloud(CACHES['A'], 180)
    target = cloud(xyz)
    truth = np.asarray(reference['controls']['known_long_baseline']['truth'])
    source = o3d.geometry.PointCloud(target)
    source.transform(np.linalg.inv(truth))
    current = np.asarray(source.points)
    source = source.select_by_index(np.flatnonzero((current[:, 0] > 3) & (np.abs(current[:, 1]) < 10)))
    seed1, seed2 = truth.copy(), truth.copy()
    seed1[0, 3] += .2
    seed2[0, 3] -= .2
    a, b = align(source, target, seed1), align(source, target, seed2)
    reverse = align(target, source, np.linalg.inv(np.asarray(a['T'])))
    cycle = np.asarray(a['T']) @ np.asarray(reverse['T'])
    point = np.array([20., 0., -1.1, 1.])
    control = dict(primary=a, alternate_seed_result=b, reverse=reverse,
        projected_disagreement_m=float(np.linalg.norm((np.asarray(a['T']) @ point - np.asarray(b['T']) @ point)[:3])),
        reverse_translation_m=float(np.linalg.norm(cycle[:3, 3])),
        reverse_rotation_deg=float(np.degrees(np.arccos(np.clip((np.trace(cycle[:3, :3]) - 1) / 2, -1, 1)))))
    control['executed_gate'] = verdict(control)
    error = np.linalg.inv(truth) @ np.asarray(a['T'])
    assert control['executed_gate'] == 'accepted' and np.linalg.norm(error[:3, 3]) < .02
    accepted = sum(row['executed_gate'] == 'accepted' for row in records)
    report = dict(status='FAR_REAL_AXIS_REFERENCE_NOT_ACCEPTED' if accepted < len(records) else 'ALL_REFERENCE_CONSISTENCY_CHECKS_PASS', rows=records,
                  gates=dict(Counter(r['executed_gate'] for r in records)), nonzero_positive_control=control)
    with (HERE / ('reference-validation-deskew.json' if args.deskew else 'reference-validation.json')).open('x') as stream:
        json.dump(report, stream, indent=2)
    print(report['gates'], 'control', control['executed_gate'], flush=True)


if __name__ == '__main__':
    main()
