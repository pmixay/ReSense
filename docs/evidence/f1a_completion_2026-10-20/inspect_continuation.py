"""Independent raw-point sketch of the registered rail-continuation condition."""
import json
from pathlib import Path

import numpy as np

WORK = Path('/tmp/opencode/f1a-completion-work')


def support(row, data):
    X, dy, h, free = (data[k] for k in ('X', 'dy', 'h', 'free'))
    x0, x1 = row['bbox'][0][0], row['bbox'][1][0]
    if row['size'][1] > 0.45:
        return None
    own = dy[data['own']]
    if not own.size:
        return None
    for side in (-1, 1):
        axis = side * 0.795
        if not own.min() <= axis + 0.1 or not own.max() >= axis - 0.1:
            continue
        bands = []
        for before in (True, False):
            points = [(float(x), float(z)) for x, d, z, f in zip(X, dy, h, free)
                      if f and own.min() <= d <= own.max() and -0.3 < z < 0.3
                      and (x0 - 5 <= x < x0 - 0.3 if before else x1 + 0.3 < x < x1 + 5)]
            if not points:
                break
            bands.append(max(points, key=lambda v: v[1]))
        if len(bands) == 2:
            (a, ha), (b, hb) = bands
            # The lower of the two interpolated endpoint heights protects sloping rails.
            line = min(ha + (x - a) * (hb - ha) / (b - a) for x in (x0, x1))
            if row['top_new'] <= line + 0.05:
                return dict(side=side, before=bands[0], after=bands[1], line=line)
    return None


def main():
    folder = WORK / 'historical-p4/trace_fix'
    results = []
    for path in sorted(folder.glob('*.fix.ndjson')):
        for row in map(json.loads, path.read_text().splitlines()):
            if not row['A'] or row['D']:
                continue
            dump = folder / (path.name.removesuffix('.fix.ndjson') + '_fix') / f"{row['stem']}_{row['k']}.npz"
            if not dump.exists():
                raise RuntimeError(dump)
            with np.load(dump) as data:
                ref = support(row, data)
            results.append(dict(piece=path.stem, stem=row['stem'], k=row['k'], distance=row['d'],
                                lateral=row['lat'], top=row['top_new'], old=row['A'], current=row['D'],
                                continuation=ref))
    with (WORK / 'continuation-sketch-own-band.json').open('x') as stream:
        json.dump(results, stream, indent=2)
    print(json.dumps(dict(checked=len(results), flips=sum(not r['current'] for r in results),
                          recovered=sum(not r['current'] and r['continuation'] is not None for r in results),
                          focal=[r for r in results if r['stem'] in
                                 ('new_data_52_0016', 'new_data_52_0018', 'new_data_52_0020',
                                  'new_data_52_0021', 'new_data_52_0023', 'new_data_112_0000',
                                  'new_data_205_0027', 'new_data_205_0031', 'doubleT_platform_0035')]), indent=2))


if __name__ == '__main__':
    main()
