"""Compare the two rails' readings in the frames with the highest flip tops."""
import json
from pathlib import Path

import numpy as np

WORK = Path('/tmp/opencode/f1a-completion-work')
FOLDER = WORK / 'historical-p4/trace_fix'
CASES = [('new_data_1', 'new_data_52_0016', 5), ('new_data_1', 'new_data_52_0023', 5),
         ('new_data_2', 'new_data_81_0027', 8), ('new_data_7', 'new_data_205_0031', 0)]


def main():
    for piece, stem, k in CASES:
        with np.load(FOLDER / f'{piece}_fix' / f'{stem}_{k}.npz') as data:
            X, dy, h, free, own = (data[key] for key in ('X', 'dy', 'h', 'free', 'own'))
        rows = [json.loads(line) for line in (FOLDER / f'{piece}.fix.ndjson').read_text().splitlines()
                if json.loads(line)['stem'] == stem and json.loads(line)['k'] == k]
        row = rows[0]
        print(f"\n=== {stem} k={k} lat={row['lat']} top_new={row['top_new']} ref_orig={row['ref_orig']} "
              f"ref_ind={row['ref_ind']}")
        for side, axis in (('right', 0.795), ('left', -0.795)):
            sel = free & (np.abs(dy - axis) < 0.12) & (h > -0.3) & (h < 0.35)
            values = sorted((round(float(x), 1), round(float(v), 3)) for x, v in zip(X[sel], h[sel]))
            print(f'  {side} rail (free, |dy-axis|<0.12): {values}')
        # the same band with the cluster's own points added
        for side, axis in (('right', 0.795), ('left', -0.795)):
            sel = (np.abs(dy - axis) < 0.12) & (h > -0.3) & (h < 0.35)
            values = sorted((round(float(x), 1), round(float(v), 3), bool(o)) for x, v, o in zip(X[sel], h[sel], own[sel]))
            print(f'  {side} rail (all): {values}')


if __name__ == '__main__':
    main()
