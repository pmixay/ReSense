"""Inspect one archived flip frame: free returns in the fragment's lateral band."""
import json
from pathlib import Path

import numpy as np

WORK = Path('/tmp/opencode/f1a-completion-work')
FOLDER = WORK / 'historical-p4/trace_fix'


def main():
    stem, k = 'new_data_52_0016', 5
    path = FOLDER / 'new_data_1_fix' / f'{stem}_{k}.npz'
    with np.load(path) as data:
        X, dy, h, free, own, fp = (data[key] for key in ('X', 'dy', 'h', 'free', 'own', 'fp'))
    rows = [json.loads(line) for line in (FOLDER / 'new_data_1.fix.ndjson').read_text().splitlines()
            if json.loads(line)['stem'] == stem and json.loads(line)['k'] == k]
    row = rows[0]
    x0, x1 = row['bbox'][0][0], row['bbox'][1][0]
    d = dy[own]
    d0, d1 = float(d.min()), float(d.max())
    print('cluster', {k: row[k] for k in ('d', 'lat', 'size', 'top_old', 'top_new', 'ref_orig', 'ref_ind')})
    print('own dy range', round(d0, 3), round(d1, 3), 'x', x0, x1, 'free points', int(free.sum()), 'of', X.size)
    for name, lo, hi in (('before', x0 - 5.0, x0 - 0.3), ('after', x1 + 0.3, x1 + 5.0), ('whole', x0 - 5.0, x1 + 5.0)):
        for label, mask in (('free', free), ('all', np.ones(X.size, bool))):
            sel = mask & (X > lo) & (X < hi) & (dy >= d0) & (dy <= d1) & (h > -0.3) & (h < 0.3)
            if not sel.any():
                print(name, label, 'none')
                continue
            near = sel & (np.abs(dy - 0.795) < 0.1)
            print(name, label, 'n=', int(sel.sum()), 'max h in band', round(float(h[sel].max()), 3),
                  'max h near axis', round(float(h[near].max()), 3) if near.any() else None,
                  'n near axis', int(near.sum()))
    # what does the narrow rail band see on the free points?
    for name, lo, hi in (('before', x0 - 5.0, x0 - 0.3), ('after', x1 + 0.3, x1 + 5.0)):
        sel = free & (X > lo) & (X < hi) & (np.abs(dy - 0.795) < 0.1) & (h > -0.3) & (h < 0.3)
        print('rail-axis free returns', name, sorted(round(float(v), 3) for v in h[sel]))
    sel = free & (X > x0 - 5.0) & (X < x1 + 5.0) & (np.abs(dy - 0.795) < 0.1) & (h > -0.3) & (h < 0.3)
    print('rail-axis free returns whole', sorted(round(float(v), 3) for v in h[sel]))


if __name__ == '__main__':
    main()
