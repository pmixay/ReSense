"""Independent raw landmark, manufactured-transform and trajectory diagnostics."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial.transform import Rotation

import direct_gicp as registration
import landmarks

WORK = Path('/tmp/opencode/h1-trajectory')


def controls():
    target, sha = registration.observed('A', 180, False)
    truth = np.eye(4)
    truth[:3, :3] = Rotation.from_euler('xyz', [.3, .1, 1.], degrees=True).as_matrix()
    truth[:3, 3] = [80., .2, .05]
    source = (target - truth[:3, 3]) @ truth[:3, :3]
    a, b = registration.overlap(source, target, truth)
    seed = truth.copy()
    seed[0, 3] += .2
    alternate = truth.copy()
    alternate[:3, :3] = alternate[:3, :3] @ Rotation.from_euler('xyz', [.1, .05, -.1], degrees=True).as_matrix()
    alternate[:3, 3] += [-.2, .05, 0]
    first = registration.align(a, b, seed, 'gicp')
    second = registration.align(a, b, alternate, 'gicp')
    reverse = registration.align(b, a, np.linalg.inv(np.asarray(first['T'])), 'gicp')
    point = np.array([15., 0., -1., 1.])
    check = registration.metrics(first, second, reverse, point)
    errors = np.linalg.inv(truth) @ np.array(first['T'])
    result = dict(source_hash=sha, truth=truth.tolist(), seed=seed.tolist(), alternate_seed=alternate.tolist(),
        primary=first, alternate=second, reverse=reverse, criteria=check,
        translation_truth_error_m=float(np.linalg.norm(errors[:3, 3])),
        rotation_truth_error_deg=float(np.linalg.norm(Rotation.from_matrix(errors[:3, :3]).as_rotvec())*180/np.pi))
    assert check['consistent'], result
    assert result['translation_truth_error_m'] < .02 and result['rotation_truth_error_deg'] < .01
    # Same validator must reject a deliberately corrupted transform.
    corrupted = dict(first)
    wrong = np.asarray(first['T']).copy()
    wrong[1, 3] += .5
    corrupted['T'] = wrong.tolist()
    negative = registration.metrics(first, corrupted, reverse, point)
    assert not negative['consistent'] and negative['projected_disagreement_m'] > .49
    result['corrupted_transform_control'] = negative
    return result


def main():
    report = dict(controls=controls(), trajectories={}, landmark_check={})
    # Independently identify the bright compact raw wall reflector in two scans.
    reflector = []
    for i in [0, 1]:
        clusters, sha, points, bright = landmarks.extract('A', i, 100)
        candidates = [c for c in clusters if 40 < c['center'][0] < 50 and -2.5 < c['center'][1] < -1.8]
        assert len(candidates) == 1, candidates
        reflector.append(dict(frame=i, source_hash=sha, cluster=candidates[0]))
    delta = np.asarray(reflector[0]['cluster']['center']) - np.asarray(reflector[1]['cluster']['center'])
    report['landmark_check'] = dict(rows=reflector, raw_centroid_displacement=delta.tolist(),
        interpretation='Raw reflector independently supports the ~1.34m longitudinal mode, not the ~0.34m alias; centroid difference is not full SE3 truth.')
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    for r, name in enumerate(['A', 'C']):
        files = [f'local-gicp-{name}-seeded.json', f'colored-{name}-sequence.json',
                 f'local-gicp-{name}-deskew1.json', f'features-{name}-sequence.json',
                 f'map-gicp-{name}-forward.json', f'map-gicp-{name}-backward.json']
        report['trajectories'][name] = []
        for file in files:
            data = json.loads((WORK / file).read_text())
            poses = np.asarray([row['pose'] for row in data['rows']])
            t = poses[:, :3, 3]
            angles = Rotation.from_matrix(poses[:, :3, :3]).as_euler('xyz', degrees=True)
            axes[r, 0].plot(t[:, 0], t[:, 1], label=file.replace(name+'-', ''))
            axes[r, 1].plot(t[:, 0], t[:, 2])
            axes[r, 2].plot(t[:, 0], angles[:, 0])
            report['trajectories'][name].append(dict(file=file, frames=len(poses),
                final_translation=t[-1].tolist(), final_euler_xyz_deg=angles[-1].tolist(),
                max_abs_roll_deg=float(np.max(np.abs(angles[:, 0]))),
                maximum_step_m=float(np.max(np.linalg.norm(np.diff(t, axis=0), axis=1)))))
        for ax, label in zip(axes[r], ['left displacement m', 'up displacement m', 'roll degrees']):
            ax.set(xlabel='forward displacement m', ylabel=label, title=name)
            ax.grid()
        axes[r, 0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(WORK / 'trajectory-methods.png', dpi=150)
    plt.close(fig)
    (WORK / 'validation-reconstruction.json').write_text(json.dumps(report, indent=2))
    print('KNOWN TRANSFORM', report['controls']['criteria'], 'truth error', report['controls']['translation_truth_error_m'], report['controls']['rotation_truth_error_deg'])
    print('RAW REFLECTOR', report['landmark_check']['raw_centroid_displacement'])
    for name, trajectories in report['trajectories'].items():
        for row in trajectories:
            print(name, row)


if __name__ == '__main__':
    main()
