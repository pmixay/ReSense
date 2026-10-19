"""Current observed far-rail support in the wall-disagreement interval."""
from dataclasses import fields
import json
from pathlib import Path

import numpy as np

from reference import CACHES, ROOT, raw_cloud
from resense.config import DetectorConfig
from resense.farrails import FarRailParams, far_rails
from resense.track import TrackModel, estimate_rails


def main():
    rows = json.loads((ROOT / 'docs/evidence/h1_axis_range_2026-10-19/trace-ranges-d.json').read_text())['cases']['A-axis']['rows']
    keys = {field.name for field in fields(TrackModel)}
    result = []
    for index in range(300, 330):
        xyz, _ = raw_cloud(CACHES['A'], index)
        with np.load(CACHES['A'] / f'f_{index:05d}.npz') as data:
            ring = data['ring']
        state = rows[index]['result']['track']
        model = TrackModel(**{k: np.asarray(v) if k == 'floor_coef' else v for k, v in state.items() if k in keys})
        near = estimate_rails(xyz, model, DetectorConfig().track, model.center, prior=model)
        far = None
        if near.xm is not None:
            args = FarRailParams(height_band=.3, cant=.1, min_stations=3, pair_max_forward_gap=1., pair_use_nearer_forward=True)
            far = far_rails(xyz, ring, model, (near.xm[-1], near.mids[-1]), args)
        record = dict(frame=index, target_x=rows[index]['info']['X'], near_slabs=near.n_slabs,
            candidates=far.n_candidates if far is not None else 0,
            stations=far.x.tolist() if far is not None else [],
            centres=far.y.tolist() if far is not None else [],
            residual=(far.y - model.center_y(far.x)).tolist() if far is not None else [])
        result.append(record)
        print(record, flush=True)
    with (Path(__file__).parent / 'far-rail-probe.json').open('x') as stream:
        json.dump(result, stream, indent=2)


if __name__ == '__main__':
    main()
