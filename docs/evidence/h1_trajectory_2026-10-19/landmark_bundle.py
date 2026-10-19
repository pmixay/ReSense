"""Reflective landmark tracks and sparse multiview SE3 bundle adjustment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares, linear_sum_assignment
from scipy.sparse import lil_matrix
from scipy.spatial.transform import Rotation

import landmarks

WORK = Path('/tmp/opencode/h1-trajectory')


def discover(name):
    seed = json.loads((WORK / f'local-gicp-{name}-seeded.json').read_text())['rows']
    poses = np.array([row['pose'] for row in seed])
    tracks = []
    manifests = []
    for i in range(len(seed)):
        objects, sha, _, _ = landmarks.extract(name, i, 30)
        manifests.append(dict(frame=i, sha256=sha, objects=objects))
        targets = np.asarray([obj['center'] for obj in objects])
        active = [(k, track[-1]) for k, track in enumerate(tracks) if i-track[-1]['frame'] <= 5]
        claimed = set()
        if active and len(objects):
            predicted = []
            for k, observation in active:
                transform = np.linalg.inv(poses[i]) @ poses[observation['frame']]
                predicted.append(transform[:3, :3] @ np.asarray(observation['center']) + transform[:3, 3])
            distances = np.linalg.norm(np.asarray(predicted)[:, None, :] - targets[None, :, :], axis=2)
            rows, cols = linear_sum_assignment(np.minimum(distances, 100))
            for row, col in zip(rows, cols, strict=True):
                if distances[row, col] > .30:
                    continue
                # Reject a genuinely ambiguous proposal rather than picking the
                # lowest cost when two nearby bright patches can swap identity.
                candidates = distances[row] <= .30
                if candidates.sum() > 1:
                    continue
                k = active[row][0]
                tracks[k].append(dict(frame=i, **objects[col], link_distance=float(distances[row, col])))
                claimed.add(col)
        for j, obj in enumerate(objects):
            if j not in claimed:
                tracks.append([dict(frame=i, **obj)])
    rows = []
    for k, track in enumerate(tracks):
        first, last = track[0]['frame'], track[-1]['frame']
        baseline = float(np.linalg.norm(poses[last, :3, 3] - poses[first, :3, 3]))
        if len(track) >= 8 and baseline >= 15:
            rows.append(dict(id=k, observations=track, baseline=baseline))
    for i, row in enumerate(rows):
        row['validation_only'] = i % 5 == 0
    result = dict(sequence=name, seed_file=f'local-gicp-{name}-seeded.json', frames=len(seed), all_tracks=len(tracks), retained=rows)
    (WORK / f'landmark-tracks-{name}.json').write_text(json.dumps(result, indent=2))
    (WORK / f'landmark-proposals-{name}.json').write_text(json.dumps(manifests, indent=2))
    print('TRACKS', name, len(tracks), 'retained', len(rows), 'train', sum(not row['validation_only'] for row in rows), 'validation', sum(row['validation_only'] for row in rows), flush=True)
    return result


def solve(data, max_nfev=100, revision='', resume=False):
    name = data['sequence']
    seed_rows = json.loads((WORK / data['seed_file']).read_text())['rows']
    poses = np.array([row['pose'] for row in seed_rows])
    n = len(poses)
    training = [row for row in data['retained'] if not row['validation_only']]
    initial_poses = np.column_stack([Rotation.from_matrix(poses[:, :3, :3]).as_rotvec(), poses[:, :3, 3]])
    landmark_positions, observations = [], []
    for k, row in enumerate(training):
        world = []
        for obs in row['observations']:
            i = obs['frame']
            point = np.array(obs['center'])
            observations.append((i, k, point))
            world.append(poses[i, :3, :3] @ point + poses[i, :3, 3])
        landmark_positions.append(np.median(world, axis=0))
    frame_index = np.array([o[0] for o in observations])
    track_index = np.array([o[1] for o in observations])
    raw_points = np.array([o[2] for o in observations])
    m = len(training)
    edge = np.array([np.asarray(row['T']) for row in seed_rows[1:]])
    x0 = np.r_[initial_poses[1:].ravel(), np.asarray(landmark_positions).ravel()]
    if resume:
        previous = json.loads((WORK / f'landmark-bundle-{name}.json').read_text())
        rp = np.asarray([row['pose'] for row in previous['rows']])
        coordinates = np.column_stack([Rotation.from_matrix(rp[:, :3, :3]).as_rotvec(), rp[:, :3, 3]])
        lm = []
        for row in training:
            lm.append(np.median([rp[obs['frame'], :3, :3] @ np.array(obs['center']) + rp[obs['frame'], :3, 3]
                                 for obs in row['observations']], axis=0))
        x0 = np.r_[coordinates[1:].ravel(), np.array(lm).ravel()]
    structure = lil_matrix((3*len(observations) + 6*(n-1), len(x0)), dtype=int)
    for j, (i, k, _) in enumerate(observations):
        if i:
            structure[3*j:3*j+3, 6*(i-1):6*i] = 1
        structure[3*j:3*j+3, 6*(n-1)+3*k:6*(n-1)+3*k+3] = 1
    start = 3*len(observations)
    for i in range(1, n):
        if i > 1:
            structure[start+6*(i-1):start+6*i, 6*(i-2):6*i] = 1
        else:
            structure[start:start+6, :6] = 1

    def unpack(x):
        coordinates = np.vstack([initial_poses[0], x[:6*(n-1)].reshape(n-1, 6)])
        return Rotation.from_rotvec(coordinates[:, :3]).as_matrix(), coordinates[:, 3:], x[6*(n-1):].reshape(m, 3)

    def residual(x):
        rot, trans, lm = unpack(x)
        mapped = np.einsum('nij,nj->ni', rot[frame_index], raw_points) + trans[frame_index]
        errors = (mapped - lm[track_index]) / .04
        relative_rot = np.einsum('nji,njk->nik', rot[:-1], rot[1:])
        rotation_error = Rotation.from_matrix(np.einsum('nji,njk->nik', edge[:, :3, :3], relative_rot)).as_rotvec() / np.radians(.05)
        relative_trans = np.einsum('nji,nj->ni', rot[:-1], trans[1:]-trans[:-1])
        translation_error = (relative_trans - edge[:, :3, 3]) / np.array([.05, .02, .02])
        return np.r_[errors.ravel(), np.column_stack([rotation_error, translation_error]).ravel()]

    solution = least_squares(residual, x0, jac_sparsity=structure.tocsr(), loss='soft_l1',
        f_scale=1., max_nfev=max_nfev, x_scale='jac', ftol=1e-6, xtol=1e-6, gtol=1e-6, verbose=1)
    rot, trans, lm = unpack(solution.x)
    refined = np.repeat(np.eye(4)[None, :, :], n, axis=0)
    refined[:, :3, :3], refined[:, :3, 3] = rot, trans
    validation = []
    for row in data['retained']:
        if not row['validation_only']:
            continue
        obs = row['observations']
        points = []
        for values in [poses, refined]:
            positions = np.array([values[o['frame'], :3, :3] @ np.array(o['center']) + values[o['frame'], :3, 3] for o in obs])
            reference = np.median(positions[:min(5, len(positions))], axis=0)
            residuals = np.linalg.norm(positions-reference, axis=1)
            points.append(dict(first_anchor=reference.tolist(), residual_p50_p95_max=np.percentile(residuals, [50, 95, 100]).tolist(), last_delta=(positions[-1]-reference).tolist()))
        validation.append(dict(id=row['id'], frames=[o['frame'] for o in obs], baseline=row['baseline'], before=points[0], after=points[1]))
    result = dict(sequence=name, success=bool(solution.success), status=solution.status, message=solution.message,
                  nfev=solution.nfev, optimality=float(solution.optimality), cost=float(solution.cost), initial_cost=float(np.sum(residual(x0)**2)/2),
                  training_landmarks=m, validation_landmarks=len(validation), validation=validation,
                  rows=[dict(i=i, pose=pose.tolist()) for i, pose in enumerate(refined)])
    suffix = '-' + revision if revision else ''
    with (WORK / f'landmark-bundle-{name}{suffix}.json').open('x') as stream:
        json.dump(result, stream, indent=2)
    print('BUNDLE', name, solution.message, 'validation', [(r['id'], np.round(r['before']['residual_p50_p95_max'][1], 3), np.round(r['after']['residual_p50_p95_max'][1], 3)) for r in validation], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['discover', 'solve'])
    parser.add_argument('--sequence', choices=['A', 'C'], required=True)
    parser.add_argument('--max-nfev', type=int, default=100)
    parser.add_argument('--revision', default='')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.phase == 'discover':
        discover(args.sequence)
    else:
        solve(json.loads((WORK / f'landmark-tracks-{args.sequence}.json').read_text()),
              args.max_nfev, args.revision, args.resume)
