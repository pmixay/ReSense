"""Direct sensor-frame near/far bed views: no registration or fitted axis."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import direct_gicp as base

WORK = Path('/tmp/opencode/h1-trajectory')


def main():
    fig, axes = plt.subplots(2, 6, figsize=(20, 8))
    rows = []
    for row_index, (name, frame) in enumerate([('A', 135), ('C', 55)]):
        points, sha = base.observed(name, frame, False)
        near = base.raw.near_rails(points)
        assert near['accepted'], (name, frame)
        for ax, station in zip(axes[row_index], [15., 30., 60., 90., 120., 150.], strict=True):
            use = (np.abs(points[:, 0]-station) < 4) & (np.abs(points[:, 1]) < 7) & (points[:, 2] < -.4) & (points[:, 2] > -3)
            selected = np.unique(points[use], axis=0)
            row = dict(sequence=name, frame=frame, source_sha256=sha, station=station,
                       raw_distinct_points=len(selected), sample_xyz=selected[::max(1, len(selected)//10)].tolist())
            rows.append(row)
            ax.scatter(selected[:, 1], selected[:, 2], s=4, c=selected[:, 0], cmap='viridis')
            if station == 15:
                for pair in near['chosen']:
                    for head in pair['heads']:
                        if abs(head['x']-station) < 4:
                            ax.scatter([head['y']], [head['z']], marker='x', c='red', s=50)
            ax.set(title=f'{name} f{frame}, X={station:g}+-4m\n{len(selected)} distinct returns',
                   xlim=(-7, 7), ylim=(-3, -.4), xlabel='sensor-frame left, m', ylabel='sensor-frame up, m')
            ax.grid()
            print(name, frame, station, len(selected), flush=True)
    fig.tight_layout()
    fig.savefig(WORK / 'raw-near-far-rails.png', dpi=160)
    (WORK / 'raw-near-far-rails.json').write_text(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
