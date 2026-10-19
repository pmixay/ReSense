"""Raw-point checks and fixed physical acceptance, independent of printed hit flags."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import runpy

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from resense.clustering import FrameRays
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.track import TrackModel

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
helpers = runpy.run_path(str(ROOT / 'tests/test_column_collision_core.py'))
cast, matched, stop = (helpers[n] for n in ['physical_column', 'matched', 'stop_history'])
normalize = runpy.run_path(str(ROOT / 'docs/evidence/integration_2026-10-16/h3_selected/helpers/frame_diff.py'))['normalize']


def jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value))


def independent_boundary(xyz, h, dy, x, anchor):
    """Python grouping of raw points; no production binning or percentile helper."""
    hypotheses = [0.]
    profiles = []
    for lo, hi in [(.4, 1.4), (1.4, 2.4)]:
        for side in [-1, 1]:
            groups = {}
            use = ((xyz[:, 0] >= 4) & (xyz[:, 0] < 250) & (h >= lo) & (h < hi)
                   & (side * dy > 1.4) & (side * dy < 5))
            for px, py, ph in zip(xyz[use, 0], dy[use], h[use], strict=True):
                groups.setdefault(int(px // 2), []).append((float(py), float(ph)))
            values = {2 * key + 1: float(np.median([v[0] for v in points])) for key, points in groups.items()
                      if len(points) >= 2 and np.ptp([v[1] for v in points]) >= .15}
            near = [v for station, v in values.items() if 8 <= station <= 28]
            local = [v for station, v in values.items() if abs(station - x) <= max(6, .16 * x)]
            if len(near) < 4 or len(local) < 2 or anchor is None:
                return None, profiles
            a, b = float(np.median(near)), float(np.median(local))
            spread = max(abs(v - a) for v in near) + max(abs(v - b) for v in local) + .1
            hypotheses += [b - a + anchor[0] - spread, b - a + anchor[1] + spread]
            profiles.append(dict(height=[lo, hi], side=side, near=near, local=local, spread=spread))
    return (min(hypotheses), max(hypotheses)), profiles


def matches(row, distance, lateral):
    return any(abs(d['distance'] - distance) < 1 and abs(d['center'][1] - lateral) < .5 for d in row['dets'])


def coverage(rows):
    visible = [r for r in rows if r.get('object_points', 1) > 0]
    near = sorted(visible, key=lambda r: r['distance'])
    held = None
    for i in range(4, len(near)):
        if sum(r['hit'] for r in near[:i + 1]) / (i + 1) >= .9:
            held = near[i]['distance']
    continuous = next((r['distance'] for i, r in enumerate(visible)
                       if r['hit'] and all(s['hit'] for s in visible[i:])), None)
    return dict(first=next((r['distance'] for r in visible if r['hit']), None), held90=held,
                continuous_from=continuous,
                matched=sum(r['hit'] for r in visible), visible=len(visible),
                missed_at_or_below_100=[r['distance'] for r in visible if r['distance'] <= 100 and not r['hit']])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [ROOT / 'resense/clustering.py', ROOT / 'resense/config.py', ROOT / 'resense/detector.py',
                        ROOT / 'configs/default.yaml', ROOT / 'ros2_ws/src/resense_ros/config/detector.yaml']}
    report = dict(source_sha256=before, full=[], outside=[], intervals=[], moving=[], controls={})
    baseline = json.loads((ROOT / 'docs/evidence/h1_core_2026-10-19/physical-sweep-c.json').read_text())
    for case in baseline['full']:
        kwargs = {k: case[k] for k in ['distance', 'lateral', 'top', 'absorbing']}
        xyz, ring, labels = cast(**kwargs)
        detector = Detector(DetectorConfig())
        rows = []
        for i in range(14):
            if detector._previous_latency_ms is not None:
                detector._previous_latency_ms = 42.
            r = detector.process(Frame(xyz, np.full(len(xyz), 35, np.float32), ring=ring, stamp=i * .1))
            rows.append(dict(i=i, dets=[d.to_dict() for d in r.detections], track=r.track.to_dict(),
                             result=normalize(r.to_dict())[0], hit=False))
            rows[-1]['hit'] = matches(rows[-1], case['distance'], case['lateral'])
        old = {r['i'] for r in case['on'] if matches(r, case['distance'], case['lateral'])}
        new = {r['i'] for r in rows if r['hit']}
        report['full'].append(dict(**kwargs, previous_matched=sorted(old), matched=sorted(new),
            lost=sorted(old - new), added=sorted(new - old), rows=rows,
            object_points=int((labels == 1).sum()), xyz_sha256=hashlib.sha256(xyz.tobytes()).hexdigest()))
    for rails in [False, True]:
        for distance in [37., 67., 109., 137.]:
            for lateral in [-1.29, 1.29, -1.5, 1.5]:
                xyz, ring, labels = cast(distance=distance, lateral=lateral, top=4.12, rails=rails)
                assert abs(lateral) - .23 > 1.05
                assert np.all(np.abs(xyz[labels == 1, 1]) > 1.05)
                for error in [-.6, -.3, 0., .3, .6]:
                    cc = matched(xyz, ring, labels, axis_error=error)
                    report['outside'].append(dict(rails=rails, distance=distance, lateral=lateral, error=error,
                        clusters=[asdict(c) for c in cc], core=any(c.collision_core for c in cc),
                        stop=any(any(stop(c)) for c in cc)))
    for distance in [37., 67., 109., 137.]:
        for error, yaw in [(0., 0.), (-.6, 0.), (.6, 0.), (0., -.004), (0., .004)]:
            xyz, ring, labels = cast(distance=distance)
            model = TrackModel(np.array([0., 0., -2.18]), (3., 120.), error, np.arctan(yaw), 0.)
            h, dy = xyz[:, 2] + 1.83, xyz[:, 1] - model.center_y(xyz[:, 0])
            rays = FrameRays(xyz, ring, h, dy, model, DetectorConfig().track)
            anchor = rays.collision_axis_anchor()
            actual = rays.collision_axis_interval(distance)
            independent, profiles = independent_boundary(xyz, h, dy, distance, anchor)
            assert actual is not None and independent is not None
            assert np.allclose(actual, independent, rtol=0., atol=1e-12)
            truth = -error - yaw * distance
            assert actual[0] <= truth <= actual[1]
            # A separately specified geometric source: raw rail-head hits on each
            # of the two boxes, without the production ridge/profile algorithm.
            head = np.abs(xyz[:, 2] + 1.83) < 1e-5
            direct_centres = []
            for left, right in zip(np.linspace(4, 30, 4)[:-1], np.linspace(4, 30, 4)[1:], strict=True):
                use = head & (xyz[:, 0] >= left) & (xyz[:, 0] < right)
                means = [float(np.median(xyz[use & (labels == lab), 1])) for lab in [2, 3]]
                direct_centres.append(float(np.mean(means)))
            assert max(abs(v) for v in direct_centres) < .04
            assert anchor[0] <= min(-error - yaw * s for s in [8.3333333, 17., 25.6666667])
            assert anchor[1] >= max(-error - yaw * s for s in [8.3333333, 17., 25.6666667])
            report['intervals'].append(dict(distance=distance, error=error, yaw=yaw, anchor=anchor,
                interval=actual, independent_interval=independent, true_residual=truth,
                raw_rail_head_centres=direct_centres, raw_head_points=int(head.sum()), profiles=profiles))
    # Input identity and trace invariance on all 364 paired frame inputs.
    original = json.loads(Path('/tmp/opencode/h1-axis-diagnosis.json').read_text())
    candidate = json.loads(Path('/tmp/opencode/h1-axis-d-diagnosis.json').read_text())
    for old, new in zip(original['cases'], candidate['cases'], strict=True):
        assert old['plain_traced_equal'] and new['plain_traced_equal']
        assert all(a['xyz_sha256'] == b['xyz_sha256'] for a, b in zip(old['rows'], new['rows'], strict=True))
        if old['moving']:
            for r in new['rows']:
                actual_hit = any(abs(d['distance'] - r['distance']) < 1
                                 and abs(d['center'][1] - old['lateral']) < .5 for d in r['result']['detections'])
                assert actual_hit == r['hit']
            report['moving'].append(dict(lateral=old['lateral'], previous=coverage(old['rows']),
                candidate=coverage(new['rows']), lost=[r['i'] for a, r in zip(old['rows'], new['rows'], strict=True)
                                                     if a['hit'] and not r['hit']]))
    report['controls']['plain_traced_equal_input_rows'] = sum(len(c['rows']) for c in original['cases'])
    xyz, ring, labels = cast()
    positive, = matched(xyz, ring, labels)
    assert positive.collision_core and any(stop(positive))
    report['controls']['positive_core_and_confirmed_STOP'] = True
    # Manufactured boundary displacement: a known nonzero consistency change.
    model = TrackModel(np.array([0., 0., -2.18]), (3., 120.), 0., 0., 0.)
    original_rays = FrameRays(xyz, ring, xyz[:, 2] + 1.83, xyz[:, 1], model, DetectorConfig().track)
    shifted = xyz.copy()
    shifted[(xyz[:, 0] > 40) & (np.abs(xyz[:, 1]) > 1.4), 1] += .7
    moved = FrameRays(shifted, ring, shifted[:, 2] + 1.83, shifted[:, 1], model, DetectorConfig().track)
    assert moved.collision_axis_interval(67.)[1] > original_rays.collision_axis_interval(67.)[1] + .5
    report['controls']['nonzero_boundary_displacement_detected'] = True
    fig, axs = plt.subplots(1, 3, figsize=(13, 4))
    for ax, distance, lateral, error in zip(axs, [109., 137., 67.], [-.68, -.68, 1.29], [0., 0., .6], strict=True):
        xyz, ring, labels = cast(distance=distance, lateral=lateral)
        obj = xyz[labels == 1]
        cc = matched(xyz, ring, labels, axis_error=error)
        ax.scatter(obj[:, 1], obj[:, 2] + 1.83, s=12, label='raw physical object')
        for edge in [-1.05, 1.05]:
            ax.axvline(edge, color='red', linestyle='--')
        ax.set(xlabel='true lateral [m]', ylabel='height above rail [m]', ylim=(0, 3.5),
               title=f'x={distance:g}, y={lateral:g}, model error={error:g}\ncore={any(c.collision_core for c in cc)}')
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(HERE / 'raw-examples-d.png', dpi=150)
    plt.close(fig)
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == sha for p, sha in before.items())
    report['source_unchanged'] = True
    report['summary'] = dict(previous_matched=sum(len(c['previous_matched']) for c in report['full']),
        matched=sum(len(c['matched']) for c in report['full']), lost=sum(len(c['lost']) for c in report['full']),
        entirely_missed=[{k: c[k] for k in ['distance', 'lateral', 'top', 'absorbing']}
                         for c in report['full'] if not c['matched']],
        outside_cases=len(report['outside']), false_cores=sum(c['core'] for c in report['outside']),
        false_stops=sum(c['stop'] for c in report['outside']))
    with args.out.open('x') as stream:
        json.dump(report, stream, default=jsonable, indent=2)
    print(json.dumps(dict(summary=report['summary'], moving=report['moving'], controls=report['controls']), indent=2))


if __name__ == '__main__':
    main()
