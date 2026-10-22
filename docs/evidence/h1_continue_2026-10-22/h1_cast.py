"""Independent physical nearest-return caster; geometry is the oracle, never a fit."""
import numpy as np
from resense.sensor import RING_ELEVATION_DEG


def cast(distance=67., lateral=.68, top=3.22, width=.46, phase=.037,
         host=True, host_height=.35, distractor=None, distractor_height=.46,
         distractor_width=.08, bed=-2.18, walls=4.1, target=True,
         shadow=False, host_start=3., distractor_start=3., shadow_top=2.29,
         shadow_distance=7., shadow_halfwidth=2.):
    az = np.deg2rad(np.arange(-50., 50.00001, .1) + phase)
    el = np.deg2rad(np.asarray(RING_ELEVATION_DEG))
    # Construct each elevation independently (no fixture/production geometry).
    directions = np.concatenate([np.column_stack((np.cos(e)*np.cos(az),
                               np.cos(e)*np.sin(az), np.full(len(az), np.sin(e)))) for e in el])
    rings = np.repeat(np.arange(len(el)), len(az))
    t = np.full(len(directions), np.inf)
    labels = np.zeros(len(t), np.int16)
    for axis, plane in ((0,247.), (1,walls), (1,-walls), (2,2.29), (2,bed)):
        np.minimum(t, np.divide(plane, directions[:,axis], out=np.full(len(t),np.inf),
                   where=(plane*directions[:,axis] > 0)), out=t)
    boxes = []
    if target:
        boxes.append((1, [distance-width/2,lateral-width/2,-1.83],
                         [distance+width/2,lateral+width/2,top-1.83]))
    if shadow:
        boxes.append((2,[shadow_distance,-shadow_halfwidth,bed],
                        [shadow_distance+2.,shadow_halfwidth,shadow_top]))
    for center, height, rw, start, first in ((0.,host_height,.08,host_start,10),
                         (distractor,distractor_height,distractor_width,distractor_start,20)):
        if center is None or (first==10 and not host):
            continue
        for j, side in enumerate((-1,1)):
            y = center + side*.795
            boxes.append((first+j,[start,y-rw/2,bed],[247.,y+rw/2,bed+height]))
    for label, lower, upper in boxes:
        entry = np.full(len(t), -np.inf)
        leave = np.full(len(t), np.inf)
        for axis in range(3):
            a = lower[axis]/directions[:,axis]
            b = upper[axis]/directions[:,axis]
            entry = np.maximum(entry,np.minimum(a,b))
            leave = np.minimum(leave,np.maximum(a,b))
        hit = (entry > 0) & (entry <= leave) & (entry < t)
        t[hit] = entry[hit]
        labels[hit] = label
    xyz = directions*t[:,None]
    keep = (t >= 2.5) & (t <= 225.)
    return xyz[keep].astype(np.float32), rings[keep], labels[keep]
