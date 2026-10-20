"""Print the footprint points that set the repaired top, with their raw coordinates."""
import json
from pathlib import Path

import numpy as np

WORK = Path('/tmp/opencode/f1a-completion-work')
FOLDER = WORK / 'historical-p4/trace_fix'
CASES = [('new_data_1', 'new_data_52_0016', 5), ('new_data_1', 'new_data_52_0017', 5),
         ('new_data_7', 'new_data_205_0031', 0), ('new_data_2', 'new_data_81_0027', 8),
         ('new_data_4', 'new_data_112_0000', 4), ('new_data_1', 'new_data_52_0023', 5)]


def main():
    for piece, stem, k in CASES:
        path = FOLDER / f'{piece}_fix' / f'{stem}_{k}.npz'
        if not path.exists():
            print('missing', path)
            continue
        with np.load(path) as data:
            X, dy, h, free, own, fp = (data[key] for key in ('X', 'dy', 'h', 'free', 'own', 'fp'))
        rows = [json.loads(line) for line in (FOLDER / f'{piece}.fix.ndjson').read_text().splitlines()
                if json.loads(line)['stem'] == stem and json.loads(line)['k'] == k]
        row = rows[0]
        x0, x1 = row['bbox'][0][0], row['bbox'][1][0]
        d = dy[own]
        d0, d1 = float(d.min()), float(d.max())
        print(f"\n=== {stem} k={k} d={row['d']} lat={row['lat']} w={row['size'][1]} top_new={row['top_new']} "
              f"ref_orig={row['ref_orig']} ref_ind={row['ref_ind']} x={x0}..{x1} dy={d0:.3f}..{d1:.3f} cause={row['cause']}")
        sel = (X >= x0) & (X <= x1) & (dy >= d0) & (dy <= d1)
        order = np.argsort(-h[sel])
        for i in order[:14]:
            idx = np.flatnonzero(sel)[i]
            print(f"   x={X[idx]:8.3f} dy={dy[idx]:7.3f} h={h[idx]:7.3f} own={bool(own[idx])} free={bool(free[idx])}")


if __name__ == '__main__':
    main()
