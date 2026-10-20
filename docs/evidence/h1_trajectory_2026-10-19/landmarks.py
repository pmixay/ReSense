"""Inspect distinctive high-reflectivity raw landmarks for independent pose anchors."""
from pathlib import Path
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

import direct_gicp as base


def extract(name, index, threshold=100):
    points, sha = base.observed(name, index, False)
    with np.load(base.raw.CACHES[name] / f'f_{index:05d}.npz') as data:
        intensity = data['inten']
    use = (points[:, 0] > 4) & (points[:, 0] < 170) & (np.abs(points[:, 1]) < 8) & (intensity >= threshold)
    selected = np.unique(points[use], axis=0)
    if not len(selected):
        return [], sha, points, selected
    pairs = cKDTree(selected).query_pairs(.25, output_type='ndarray')
    graph = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(selected), len(selected)))
    n, labels = connected_components(graph, directed=False)
    clusters = []
    for i in range(n):
        p = selected[labels == i]
        if len(p) < 3 or np.ptp(p, axis=0).max() > 1.:
            continue
        clusters.append(dict(center=np.mean(p, axis=0).tolist(), size=np.ptp(p, axis=0).tolist(), n=len(p), points=p.tolist()))
    return clusters, sha, points, selected


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--threshold', type=float, default=100)
    args = parser.parse_args()
    report = {}
    fig, axes = plt.subplots(2, 2, figsize=(15, 8))
    for row, name in enumerate(['A', 'C']):
        report[name] = []
        for col, index in enumerate([0, 100]):
            clusters, sha, points, selected = extract(name, index, args.threshold)
            report[name].append(dict(frame=index, sha256=sha, clusters=clusters))
            print(name, index, 'high_intensity_raw', len(selected), 'clusters', len(clusters),
                  'centers', [np.round(c['center'], 2).tolist() for c in clusters], flush=True)
            ax = axes[row, col]
            ax.scatter(points[::30, 0], points[::30, 1], s=.2, c='0.8')
            ax.scatter(selected[:, 0], selected[:, 1], s=1, c='orange')
            for k, c in enumerate(clusters):
                x, y, _ = c['center']
                ax.text(x, y, str(k), fontsize=8)
            ax.set(title=f'{name} {index}', ylim=(-8, 8), xlim=(0, 175), xlabel='forward m', ylabel='left m')
    work = Path('/tmp/opencode/h1-trajectory')
    fig.tight_layout()
    fig.savefig(work / f'landmarks-{args.threshold:g}.png', dpi=160)
    (work / f'landmarks-{args.threshold:g}.json').write_text(json.dumps(report, indent=2))
