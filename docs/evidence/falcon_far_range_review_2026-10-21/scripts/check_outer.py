"""Closed-form outer_wall vs the sampled loop on real frames (instrumentation must not change results)."""
import sys, time
import numpy as np
sys.path.insert(0, '/home/user/rv/s')
import scene_run as S
for f in (1300, 2800):
    xyz = np.load(f'/home/user/data/falcon/f_{f:05d}.npz')['xyz']
    for xc, R, d in ((120, 300, 1), (150, 300, -1), (200, 1000, 1)):
        p = xyz.astype(np.float64).copy()
        p[:, 1] += d * S.arc(p[:, 0], xc, R)
        t = time.time(); A = S.outer_wall_loop(p, xc, R, d, 2.0); t1 = time.time() - t
        t = time.time(); B = S.outer_wall(p, xc, R, d, 2.0); t2 = time.time() - t
        ma, mb = np.any(A != p, axis=1), np.any(B != p, axis=1)
        dist = np.linalg.norm(A - B, axis=1)
        print(f, xc, R, d, 'moved loop/closed', ma.sum(), mb.sum(), 'both', (ma & mb).sum(), 'max |diff| m', round(float(dist.max()), 3),
              'p99', round(float(np.percentile(dist[ma | mb], 99)), 3) if (ma | mb).any() else 0, 's', round(t1, 2), round(t2, 3))
