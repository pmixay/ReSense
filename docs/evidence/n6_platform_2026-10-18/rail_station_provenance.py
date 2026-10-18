#!/usr/bin/env python3
"""Attribute every accepted N6 station's actual peak returns to exact source XYZ."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import warnings
from pathlib import Path

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(key, '1')
SOURCE = Path('/home/resense/data/n6/source_745096f')
sys.path.insert(0, str(SOURCE))
import numpy as np  # noqa: E402
from resense.farrails import FarRailParams, _shift, ring_pairs  # noqa: E402
from resense.track import TrackModel  # noqa: E402

HERE = Path(__file__).parent
CACHE = Path('/home/resense/data/decoded')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paired_peak_indices(xyz, ring, ref_y, rail_z, s_min, p):
    """Diagnostic copy of ring_pairs with point indices; checked against its output."""
    x, y, z = xyz.T
    sel = np.flatnonzero((ring >= 0) & (x > s_min) & (x < p.x_max))
    off = y[sel] - ref_y(x[sel])
    h = z[sel] - rail_z(x[sel])
    keep = (np.abs(off) < p.reach) & (np.abs(h) < p.height_band)
    sel, off, h = sel[keep], off[keep], h[keep]
    rows_u, row = np.unique(ring[sel], return_inverse=True)
    n_col = int(np.ceil(2.0 * p.reach / p.cell))
    col = np.clip(((off + p.reach) // p.cell).astype(np.int64), 0, n_col - 1)
    cell = row.astype(np.int64) * n_col + col
    order = np.lexsort((h, cell))
    cell_sorted = cell[order]
    last = np.r_[cell_sorted[1:] != cell_sorted[:-1], True]
    top = order[last]
    shape = (rows_u.size, n_col)
    grid_h, grid_o, grid_x = (np.full(shape, np.nan) for _ in range(3))
    grid_idx = np.full(shape, -1, dtype=int)
    grid_h.flat[cell_sorted[last]] = h[top]
    grid_o.flat[cell_sorted[last]] = off[top]
    grid_x.flat[cell_sorted[last]] = x[sel][top]
    grid_idx.flat[cell_sorted[last]] = sel[top]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        around = np.stack([_shift(grid_h, k) for k in (-3, -2, -1, 1, 2, 3)])
        n_around = np.isfinite(around).sum(axis=0)
        median = np.nanmedian(around, axis=0)
        side = np.nanmax(np.stack([_shift(grid_h, -1), _shift(grid_h, 1)]), axis=0)
    peak = (np.isfinite(grid_h) & (n_around >= 2) & (grid_h - median >= p.bump)
            & ~(grid_h < np.where(np.isfinite(side), side, -np.inf)))
    out, ids = [], []
    for r in np.flatnonzero(peak.any(axis=1)):
        c = np.flatnonzero(peak[r])
        o, hh, xx = grid_o[r, c], grid_h[r, c], grid_x[r, c]
        gap = o[None, :] - o[:, None]
        ok = (np.triu(np.ones((c.size, c.size), bool), 1)
              & (np.abs(gap - p.gauge) < p.gauge_tol)
              & (np.abs(hh[None, :] - hh[:, None]) < p.cant)
              & (np.abs(xx[None, :] - xx[:, None]) <= p.pair_max_forward_gap))
        for i, j in zip(*np.nonzero(ok)):
            out.append((min(xx[i], xx[j]), (o[i] + o[j]) / 2.0, gap[i, j]))
            ids.append((grid_idx[r, c[i]], grid_idx[r, c[j]]))
    cand, indices = np.asarray(out), np.asarray(ids)
    if not len(cand):
        return np.empty((0, 3)), np.empty((0, 2), dtype=int)
    keep = (np.abs(cand[:, 1]) < p.max_offset) & (cand[:, 0] > s_min)
    cand, indices = cand[keep], indices[keep]
    _, first = np.unique(np.round(cand[:, :2], 2), axis=0, return_index=True)
    order = np.sort(first)
    return cand[order], indices[order]


def main():
    probe = HERE / 'exact_source_rail_support.json'
    data = json.loads(probe.read_text())
    rows = []
    for entry in data['rows']:
        i = entry['frame']
        with np.load(CACHE / f'synthetic_platform/f_{i:05d}.npz') as cloud:
            raw = cloud['xyz']
            xyz = np.column_stack((-raw[:, 1], raw[:, 0], raw[:, 2]))
            rings = cloud['ring'].copy()
        with np.load(CACHE / f'cloud_with_fake_obj/f_{i + 1195:05d}.npz') as cloud:
            source_raw = cloud['xyz']
        source_members = {point.tobytes() for point in np.ascontiguousarray(source_raw)}
        model = TrackModel(**entry['pre_extension_model'])
        anchor = entry['variants']['synthetic']['near_seed']
        params = FarRailParams(x_max=80., gauge=1.59, height_band=.3, cant=.1,
                               max_gap=10., min_stations=3, pair_max_forward_gap=5.,
                               pair_use_nearer_forward=True)

        def ref_y(xv):
            return model.center + float(np.tan(model.yaw)) * np.asarray(xv, dtype=np.float64)

        candidates, ids = paired_peak_indices(xyz, rings, ref_y, model.rail_z, anchor[0] + .5, params)
        production = ring_pairs(xyz, rings, ref_y, model.rail_z, anchor[0] + .5, params)
        if not np.array_equal(candidates, production):
            raise AssertionError(f'provenance copy differs from production candidates frame {i}')
        stations = []
        for x, y in zip(entry['variants']['synthetic']['accepted_station_x'],
                        entry['variants']['synthetic']['accepted_station_y']):
            match = np.flatnonzero((np.abs(candidates[:, 0] - x) < 1e-7)
                                  & (np.abs(candidates[:, 1] + ref_y(x) - y) < 1e-7))
            if not len(match):
                raise AssertionError(f'no raw candidate for accepted station {i}/{x}')
            pair_indices = ids[match[0]]
            stations.append({'x': x, 'y': y, 'axis_residual_m': float(y - model.center_y(x)),
                             'head_indices': pair_indices.tolist(),
                             'head_xyz_vehicle': xyz[pair_indices].tolist(),
                             'head_heights_above_fitted_rail_m': (xyz[pair_indices, 2] - model.rail_z(xyz[pair_indices, 0])).tolist(),
                             'ring_ids': rings[pair_indices].tolist(),
                             'heads_both_exact_source': all(raw[j].tobytes() in source_members for j in pair_indices)})
        rows.append({'frame': i, 'stations': stations})
    report = {'method': 'Diagnostic ring-pair reproduction retains peak point indices; exact equality with production ring_pairs verified in every supported frame. Each chosen head raw float32 XYZ is checked for exact membership in matching source frame i+1195, independent of intensity and labels.',
              'supported_frames': len(rows), 'stations': sum(len(row['stations']) for row in rows),
              'non_source_head_stations': [{'frame': row['frame'], 'station': station}
                                           for row in rows for station in row['stations']
                                           if not station['heads_both_exact_source']],
              'source_probe_sha256': digest(probe), 'script_sha256': digest(Path(__file__)),
              'farrails_sha256': digest(SOURCE / 'resense/farrails.py'), 'rows': rows}
    (HERE / 'rail_station_provenance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
