"""Print the axis-band returns with positions for selected archived flip frames."""
import json
from pathlib import Path

import numpy as np

WORK = Path('/tmp/opencode/f1a-completion-work')
FOLDER = WORK / 'historical-p4/trace_fix'
CASES = [('new_data_1', 'new_data_52_0016', 5), ('new_data_1', 'new_data_52_0021', 0),
         ('new_data_7', 'new_data_205_0031', 0), ('new_data_4', 'new_data_112_0000', 7),
         ('new_data_2', 'new_data_81_0027', 8), ('new_data_7', 'new_data_205_0027', 1)]


def main():
    for piece, stem, k in CASES:
        path = FOLDER / f'{piece}_fix' / f'{stem}_{k}.npz'
        if not path.exists():
            print('missing', path)
            continue
        with np.load(path) as data:
            X, dy, h, free, own = (data[key] for key in ('X', 'dy', 'h', 'free', 'own'))
        rows = [json.loads(line) for line in (FOLDER / f'{piece}.fix.ndjson').read_text().splitlines()
                if json.loads(line)['stem'] == stem and json.loads(line)['k'] == k]
        row = rows[0]
        x0, x1 = row['bbox'][0][0], row['bbox'][1][0]
        axis = 0.795 if row['lat'] > 0 else -0.795
        print(f"\n=== {stem} k={k} d={row['d']} lat={row['lat']} w={row['size'][1]} "
              f"top_old={row['top_old']} top_new={row['top_new']} ref_orig={row['ref_orig']} ref_ind={row['ref_ind']} "
              f"x={x0}..{x1} cause={row['cause']}")
        for label, mask in (('free', free), ('own', own)):
            sel = mask & (np.abs(dy - axis) < 0.15) & (h > -0.3) & (h < 0.4)
            order = np.argsort(X[sel])
            print(' ', label, [(round(float(X[sel][i]), 2), round(float(h[sel][i]), 3)) for i in order])


if __name__ == '__main__':
    main()
