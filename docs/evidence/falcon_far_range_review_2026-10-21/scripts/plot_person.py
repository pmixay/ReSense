"""Raw points around the candidate's STOP detection at the episode onsets (and the same box in background frame 1400):
side view (along vs height) and top view (along vs lateral), track-reference coordinates."""
import json, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
T = json.load(open('/home/user/ReSense/docs/evidence/falcon_long_range_2026-10-19/track_reference.json'))['track']
rows = {r['i']: r for r in (json.loads(l) for l in open(sys.argv[1]))}
frames = [int(x) for x in sys.argv[2].split(',')]
fig, ax = plt.subplots(2, len(frames) + 1, figsize=(3.2 * (len(frames) + 1), 6))
def tr(xyz):
    x = xyz[:, 0]; return x, xyz[:, 1] - (T['a'] + T['b'] * x), xyz[:, 2] - (T['z0'] + T['c'] * x)
c0 = None
for k, f in enumerate(frames + [1400]):
    xyz = np.load(f'/home/user/data/falcon/f_{f:05d}.npz')['xyz'].astype(float)
    if f != 1400:
        r = rows[f]; d = r['dets'][0]; c = np.asarray(d['c']) @ np.asarray(r['mount_rotation']); c0 = c
        title = f"frame {f}: STOP det {d['d']} m, n={d['n']}"
    else:
        c = c0; title = "background frame 1400, same box"
    x, lat, h = tr(xyz)
    m = (np.abs(x - c[0]) < 4) & (np.abs(lat - (c[1] - T['a'])) < 2.5) & (h > -0.5) & (h < 3)
    ax[0, k].scatter(x[m] - c[0], h[m], s=6); ax[0, k].set_title(title, fontsize=8); ax[0, k].set_xlabel('along - det (m)'); ax[0, k].set_ylabel('h above rail head (m)')
    ax[0, k].set_xlim(-4, 4); ax[0, k].set_ylim(-0.5, 3)
    ax[1, k].scatter(x[m] - c[0], lat[m], s=6, c=h[m], vmin=-0.5, vmax=2); ax[1, k].set_xlabel('along - det (m)'); ax[1, k].set_ylabel('lateral (m)')
    ax[1, k].set_xlim(-4, 4); ax[1, k].set_ylim(-2.5, 2.5)
plt.tight_layout(); plt.savefig(sys.argv[3], dpi=80)
