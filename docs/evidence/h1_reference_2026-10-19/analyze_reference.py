"""Cross-view rail reference, method disagreement and raw profiles."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from reference import CACHES, HERE, WORK, near_rails, pcd, raw_cloud, register


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--revision', default='first')
    args = parser.parse_args()
    report = dict(sequences={}, samples=[])
    fig, axs = plt.subplots(2, 3, figsize=(15, 8))
    for name, start, row_axes in [('A', 180, axs[0]), ('C', 50, axs[1])]:
        suffix = '' if args.revision == 'first' else '-' + args.revision
        data = json.loads((WORK / f'sequence-{name}{suffix}.json').read_text())
        rows = data['rows']
        cache = CACHES[name]
        baseline = json.loads(Path(str(cache) + '_baseline.json').read_text())
        poses = np.asarray([r['pose'] for r in rows])
        alt = np.asarray([r['alternate_pose'] for r in rows])
        accepted = [r['i'] for r in rows if r['rails']['accepted']]
        snapshot = dict(frames=len(rows), accepted_near_frames=accepted, reference=[], closures=[])
        for r in rows:
            if r['i'] % 25 == 0 or r['i'] in [180, 200, 300]:
                sample = dict(sequence=name, frame=r['i'], accepted=r['rails']['accepted'],
                    reason=r['rails']['reason'], slab_pairs=[[dict(station=p['station'], centre=p['centre'],
                        spacing=p['spacing'], heads=p['heads']) for p in slab['pairs']] for slab in r['rails']['slabs']])
                report['samples'].append(sample)
                print('NEAR', name, r['i'], sample['reason'],
                      [[(round(p['centre'], 3), round(p['spacing'], 3)) for p in pairs] for pairs in sample['slab_pairs']], flush=True)
        for i in range(0, len(rows), 5):
            candidates = []
            for j in accepted:
                if j <= i:
                    continue
                transform = np.linalg.inv(poses[i]) @ poses[j]
                alternate = np.linalg.inv(alt[i]) @ alt[j]
                for pair in rows[j]['rails']['chosen']:
                    point = np.array([np.mean([h[k] for h in pair['heads']]) for k in ['x', 'y', 'z']] + [1.])
                    q, qa = (t @ point for t in [transform, alternate])
                    if 30 <= q[0] <= 170:
                        candidates.append(dict(j=j, xyz=q[:3].tolist(), alternate_xyz=qa[:3].tolist()))
            bins = []
            for x0 in range(30, 170, 5):
                samples = [c for c in candidates if x0 <= c['xyz'][0] < x0 + 5]
                if len({s['j'] for s in samples}) < 3:
                    continue
                x = float(np.median([s['xyz'][0] for s in samples]))
                y = np.asarray([s['xyz'][1] for s in samples])
                ya = np.asarray([s['alternate_xyz'][1] for s in samples])
                sx = np.asarray([s['xyz'][0] for s in samples])
                local_fit = np.polyfit(sx - x, y, 1)
                detrended = y - np.polyval(local_fit, sx - x)
                b = baseline[i]
                grid = np.linspace(max(3, x - 10), x + 10, 100)
                yy = b['center'] + np.tan(b['yaw']) * grid + .5 * b['curv'] * grid ** 2
                lo, hi = b['floor_range']
                xc = np.clip(grid, lo, hi)
                c2, c1, c0 = b['floor_coef']
                zz = c2 * xc ** 2 + c1 * xc + c0 + (2 * c2 * xc + c1) * (grid - xc) + b['rail_offset']
                curve = np.stack([grid, yy, zz], 1) @ np.asarray(b['R'])
                model = float(np.interp(x, curve[:, 0], curve[:, 1]))
                bins.append(dict(x=x, median_y=float(np.median(y)), model_y=model,
                    model_error=float(model - np.median(y)), support=len(samples), frames=len({s['j'] for s in samples}),
                    cross_view_span=float(np.ptp(y)), detrended_max_residual=float(np.max(np.abs(detrended))),
                    method_disagreement=float(np.max(np.abs(y - ya))),
                    reference_consistent=bool(np.max(np.abs(detrended)) <= .10 and np.max(np.abs(y - ya)) <= .15),
                    samples=samples))
            if bins:
                snapshot['reference'].append(dict(frame=i, bins=bins))
        # Cross-view registration checks a composed 10-frame transform using a
        # directly aligned cloud, rather than accepting accumulated transforms.
        for i in range(20, len(rows), 40):
            xyz, _ = raw_cloud(cache, i)
            previous, _ = raw_cloud(cache, i - 10)
            composed = np.linalg.inv(poses[i - 10]) @ poses[i]
            direct = register(pcd(xyz), pcd(previous), composed)
            delta = np.linalg.inv(composed) @ np.asarray(direct['T'])
            snapshot['closures'].append(dict(frame=i, direct=direct, composed=composed.tolist(),
                translation_error=float(np.linalg.norm(delta[:3, 3])),
                yaw_error_deg=float(np.degrees(np.arctan2(delta[1, 0], delta[0, 0])))))
        report['sequences'][name] = snapshot
        legacy_path = (Path('/tmp/opencode/r3-h1/baseline') if name == 'A' else Path('/tmp/opencode/r3-h1/supplement-range')) / ('icp_' + cache.name + '.json')
        legacy = json.loads(legacy_path.read_text())
        legacy_dx = dict(zip(legacy['i'], legacy['dx'], strict=True))
        delta = [dict(frame=r['i'], primary_dx=r['primary']['T'][0][3], old_dx=legacy_dx[r['i']],
                      delta=r['primary']['T'][0][3] - legacy_dx[r['i']]) for r in rows[1:] if r['i'] in legacy_dx]
        snapshot['forward_step_comparison'] = delta
        print('LEGACY', name, 'abs_delta_p50_p95_max', np.percentile([abs(d['delta']) for d in delta], [50, 95, 100]),
              'max_speed', max(r['speed_mps'] for r in rows[1:]), flush=True)
        xyz, _ = raw_cloud(cache, start)
        rail = near_rails(xyz)
        slab = rail['slabs'][1]
        select = (xyz[:, 0] >= 13) & (xyz[:, 0] < 20) & (np.abs(xyz[:, 1]) < 2.2) & (xyz[:, 2] < -.4)
        raw = xyz[select]
        row_axes[0].scatter(raw[:, 1], raw[:, 2], s=.5)
        row_axes[0].set(title=f'{name} k{start}: raw near slab', xlabel='Y [m]', ylabel='raw Z [m]')
        profile = slab['profile']
        row_axes[1].plot(profile['y'], profile['height'], '.-', label='height p85')
        row_axes[1].plot(profile['y'], profile['prominence'], '.-', label='prominence')
        row_axes[1].set(title='independent raw ridge profile', xlabel='Y [m]')
        row_axes[1].legend()
        candidates = next((r['bins'] for r in snapshot['reference'] if r['frame'] == start), [])
        for b in candidates:
            row_axes[2].scatter([p['xyz'][0] for p in b['samples']], [p['xyz'][1] for p in b['samples']], s=5, color='blue')
        row_axes[2].plot([b['x'] for b in candidates], [b['model_y'] for b in candidates], color='red', label='evaluated axis')
        row_axes[2].set(title=f'{name} k{start}: future near rails -> current', xlabel='X [m]', ylabel='Y [m]')
        row_axes[2].legend()
        print('SUMMARY', name, 'near accepted', len(accepted), 'reference_frames', len(snapshot['reference']),
              'closure_max', max(c['translation_error'] for c in snapshot['closures']),
              'yaw_closure_max', max(abs(c['yaw_error_deg']) for c in snapshot['closures']), flush=True)
        for distance in [(30, 60), (60, 100), (100, 150)]:
            values = [b for r in snapshot['reference'] for b in r['bins'] if distance[0] <= b['x'] < distance[1]]
            if values:
                print('RANGE', name, distance, len(values), 'axis_abs_error_p50_p95',
                    np.percentile([abs(v['model_error']) for v in values], [50, 95]),
                    'method_p95', np.percentile([v['method_disagreement'] for v in values], 95),
                    'crossview_span_p95', np.percentile([v['cross_view_span'] for v in values], 95), flush=True)
                consistent = [v for v in values if v['reference_consistent']]
                print('CONSISTENT', name, distance, len(consistent), 'of', len(values),
                    'axis_abs_error_p50_p95', np.percentile([abs(v['model_error']) for v in consistent], [50, 95]) if consistent else None,
                    flush=True)
    fig.tight_layout()
    fig.savefig(HERE / f'reference-raw-{args.revision}.png', dpi=150)
    with args.out.open('x') as stream:
        json.dump(report, stream, indent=2)


if __name__ == '__main__':
    main()
