"""Apply the production continuation rule to P4's archived flip snapshots.

The archive holds the 98 flipped clusters' raw frames (X, dy, h), the cluster's
own points, the footprint mask and the low-free mask. The production rule is
re-implemented here by importing it from the candidate tree, so the numbers are
the production branch's, not a sketch.
"""
import importlib.util
import json
import os
from pathlib import Path

import numpy as np

WORK = Path('/tmp/opencode/f1a-completion-work')
ROOT = Path(os.environ.get('RESENSE_REPO', '/tmp/opencode/f1a-completion-checkout'))
os.environ.setdefault('PYTHONPATH', str(ROOT))
import sys  # noqa: E402
sys.path.insert(0, str(ROOT))

from resense.config import LowObjectConfig  # noqa: E402
from resense.lowobj import _rail_surface_reference  # noqa: E402

CFG = LowObjectConfig()


class Cluster:
    def __init__(self, row):
        self.bbox_min = np.array(row['bbox'][0])
        self.bbox_max = np.array(row['bbox'][1])
        self.lateral = row['lat']
        self.size = np.array(row['size'])
        self.distance = row['d']
        self.height_max = row['top_old']


def main():
    folder = WORK / 'historical-p4/trace_fix'
    results = []
    for path in sorted(folder.glob('*.fix.ndjson')):
        for row in map(json.loads, path.read_text().splitlines()):
            if not row['A'] or row['D']:
                continue
            dump = folder / (path.name.removesuffix('.fix.ndjson') + '_fix') / f"{row['stem']}_{row['k']}.npz"
            with np.load(dump) as data:
                X, dy, h, free, own = (data[k] for k in ('X', 'dy', 'h', 'free', 'own'))
                c = Cluster(row)
                d = dy[own]
                surface = _rail_surface_reference(c, X[free], dy[free], h[free],
                                                  float(d.min()), float(d.max()), CFG, 1.59)
                results.append(dict(stem=row['stem'], piece=path.stem, k=row['k'], distance=row['d'],
                                    lateral=row['lat'], top_old=row['top_old'], top_new=row['top_new'],
                                    width=row['size'][1],
                                    ref_orig=row['ref_orig'], ref_ind=row['ref_ind'],
                                    cause=row['cause'], surface=surface,
                                    recovered=bool(surface is not None
                                                   and row['top_new'] <= surface + CFG.rail_start_margin)))
    recovered = [r for r in results if r['recovered']]
    missed = [r for r in results if not r['recovered']]
    print(json.dumps(dict(flips=len(results), recovered=len(recovered), missed=len(missed),
                          recovered_rows=[(r['stem'], r['k'], r['distance'], r['lateral'], r['top_new'],
                                           r['surface']) for r in recovered],
                          missed_rows=[(r['stem'], r['k'], r['distance'], r['lateral'], r['top_new'],
                                        r['surface'], r['cause']) for r in missed]), indent=2))
    (WORK / 'continuation-production.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
