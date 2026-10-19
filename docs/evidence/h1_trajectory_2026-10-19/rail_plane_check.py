"""Fit raw paired head observations to a local plane, without a detector."""
import json
from pathlib import Path

import numpy as np

WORK = Path('/tmp/opencode/h1-reference')


def plane(row):
    points = [list(head[k] for k in ['x', 'y', 'z']) for slab in row['rails']['slabs']
              if len(slab['pairs']) == 1 for head in slab['pairs'][0]['heads']]
    if len(points) < 4:
        return None
    xyz = np.asarray(points)
    matrix = np.column_stack([xyz[:, :2], np.ones(len(xyz))])
    coeff, *_ = np.linalg.lstsq(matrix, xyz[:, 2], rcond=None)
    residual = xyz[:, 2] - matrix @ coeff
    return dict(coef=coeff.tolist(), residual_max=float(np.max(np.abs(residual))),
                roll_deg=float(np.degrees(np.arctan(coeff[1]))),
                pitch_deg=float(np.degrees(np.arctan(coeff[0]))), heads=points)


if __name__ == '__main__':
    for name in ['A', 'C']:
        rows = json.loads((WORK / f'sequence-{name}-v2.json').read_text())['rows']
        accepted = [dict(frame=row['i'], **result) for row in rows if (result := plane(row)) is not None]
        print(name, 'planes', len(accepted), '/', len(rows), 'residual_max_percentiles', np.percentile([row['residual_max'] for row in accepted], [50, 95, 100]))
        for row in accepted[::20]:
            print(name, {key: value for key, value in row.items() if key != 'heads'})
