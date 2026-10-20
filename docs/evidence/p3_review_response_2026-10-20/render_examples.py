"""Inspect raw controlled B4 supports and the original P4 raised-rail points."""
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'docs/evidence/p4_review_shipping_2026-10-20/scripts'))
from f1a_capped_top import scene


def main():
    b4 = json.loads((HERE / 'b4.json').read_text())
    examples = [next(row for row in b4['cases'] if row['shape'] == shape
                     and row['x'] == x and row['mount_error'] == error)
                for shape, x, error in [('hanging', 5., 0.), ('hanging', 5., .8),
                                        ('hanging', 20., 1.6), ('person', 5., 3.2)]]
    figure, axes = plt.subplots(1, 4, figsize=(16, 4.6))
    for axis, row in zip(axes, examples, strict=True):
        xyz = np.array(row['raw_xyz'])
        true = xyz[:, 2] + 1.83
        supplied = xyz[:, 2] + row['mount_height']
        axis.axhspan(.12, 3., color='#cfe8cd', alpha=.65, label='true envelope height')
        axis.scatter(np.zeros(len(true)), true, s=20, label='true height')
        axis.scatter(np.ones(len(true)), supplied, s=20, label='height from supplied mount')
        axis.axhline(3., color='black', linewidth=.8)
        axis.set_xticks([0, 1], ['true', 'supplied'])
        axis.set_ylim(0, 5.5)
        axis.set_ylabel('Height above rail, m')
        axis.set_title(f"{row['shape']}, x={row['x']:g} m\nerror=+{row['mount_error']:g} m; demoted={row['demoted']}")
        print('B4 RAW', row['shape'], row['x'], row['mount_error'],
              'true min/max', true.min(), true.max(), 'mount min/max', supplied.min(), supplied.max(),
              'demoted', row['demoted'])
    axes[0].legend(fontsize=7, loc='upper left')
    figure.suptitle('Controlled component inputs: this is mount-state fault injection, not measured field exposure')
    figure.tight_layout()
    figure.savefig(HERE / 'b4-raw-examples.png', dpi=130)
    plt.close(figure)

    frame, head = scene(.18, 40., .12)
    records = json.loads((HERE / 'f1a.json').read_text())
    expected = next(c for c in records if c['rail_rise'] == .18 and c['top_above_true_rail'] == .12 and c['enabled'])
    assert hashlib.sha256(frame.xyz.tobytes()).hexdigest() == expected['input_xyz_sha256']
    x, y, z = frame.xyz.T
    selected = (x >= 39.) & (x <= 41.) & (np.abs(y - .25) <= 1.2) & (z <= head + .5)
    raw = frame.xyz[selected]
    figure, axis = plt.subplots(figsize=(8, 4))
    axis.scatter(raw[:, 1], raw[:, 2] - head, s=14)
    axis.axhline(0., color='black', label='true rail head')
    axis.axhline(.12, color='red', label='true box top')
    axis.set(xlabel='Raw Y, m', ylabel='Z above true raised head, m',
             title='P4 B1 raw cross-section, X=39..41 m; 0.18 m rail rise')
    axis.legend()
    figure.tight_layout()
    figure.savefig(HERE / 'f1a-raw-example.png', dpi=150)
    plt.close(figure)
    with (HERE / 'raw-examples.json').open('x') as stream:
        json.dump({'b4': examples, 'f1a_raw_selected_xyz': raw.tolist(),
                   'f1a_input_sha256': expected['input_xyz_sha256'], 'true_raised_head_z': head}, stream, indent=2)
        stream.write('\n')
    print('F1a RAW selected points', len(raw), 'head Z', head, 'known matched STOP rows', expected['matched_STOP_rows'])


if __name__ == '__main__':
    main()
