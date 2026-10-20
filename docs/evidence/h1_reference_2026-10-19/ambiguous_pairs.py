"""Physical adjacent rail-pair ambiguity, not a supplied coordinate shift alone."""
import json
from pathlib import Path
import runpy

from resense.config import DetectorConfig
from resense.track import TrackModel
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
helper = runpy.run_path(str(ROOT / 'tests/test_column_collision_core.py'))
cast, matched, stop = (helper[n] for n in ['physical_column', 'matched', 'stop_history'])
from resense.clustering import FrameRays  # noqa: E402


def main():
    rows = []
    for phase in [-.049, 0., .037, .049]:
        for distance in [17., 37., 67.]:
            for side in [-1, 1]:
                for error in [-.6, 0., .6]:
                    xyz, ring, labels = cast(distance=distance, lateral=side * 1.29, top=4.12,
                        wall_left=4.1, wall_right=-4.1, extra_rails=[side * 2.385], azimuth_phase=phase)
                    model = TrackModel(np.array([0., 0., -2.18]), (3., 120.), error, 0., 0.)
                    rays = FrameRays(xyz, ring, xyz[:, 2] + 1.83, xyz[:, 1] - error, model, DetectorConfig().track)
                    cc = matched(xyz, ring, labels, axis_error=error)
                    rows.append(dict(phase=phase, distance=distance, side=side, error=error,
                        anchor=rays.collision_axis_anchor(), interval=rays.collision_axis_interval(distance),
                        core=any(c.collision_core for c in cc), STOP=any(any(stop(c)) for c in cc)))
    output = HERE / 'ambiguous-pairs-first.json'
    with output.open('x') as stream:
        json.dump(rows, stream, indent=2)
    bad = [r for r in rows if r['core'] or r['STOP']]
    print('CASES', len(rows), 'FALSE', len(bad), bad, flush=True)


if __name__ == '__main__':
    main()
