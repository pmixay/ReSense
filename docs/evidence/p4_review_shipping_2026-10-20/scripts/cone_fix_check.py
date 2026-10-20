"""Review A finding 1, proposed fix (not applied): candidate fix - accept a one-sided axis as forward only when the returns lie in a bounded cone about
it (p98 angle < 80 deg); a half-space of ground below a sensor is not a directional FOV."""
import sys, numpy as np
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scene import rays, cast, frame
import resense.calibration as cal
from resense.calibration import orientation_candidates
orig = cal.directional_axes
def patched(xyz):
    fw, up = orig(xyz)
    if fw is None:
        return fw, up
    p = xyz[::max(1, int(np.ceil(len(xyz) / 16384)))].astype(np.float64)
    n = np.linalg.norm(p, axis=1)
    p = p[np.isfinite(p).all(axis=1) & (n > 1.0)]
    cosang = (p @ fw) / np.linalg.norm(p, axis=1)
    if np.degrees(np.arccos(np.clip(np.percentile(cosang, 2), -1, 1))) > 80.0:
        return None, None
    return fw, up
def _fov():
    az, el = np.meshgrid(np.linspace(-1.0, 1.0, 130), np.linspace(-.20, .10, 20))
    p = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], -1).reshape(-1, 3)
    return (p * np.linspace(4, 100, len(p))[:, None]).astype(np.float32)
ok = sum(np.array_equal(patched(_fov() @ R.T)[0], R[:, 0]) for R in orientation_candidates())
print("project fixture, 24 rotations, forward kept:", ok, "/ 24")
for name, az, kw in [("pandar50 tunnel", (-50, 50), dict(tunnel=True)), ("pandar210 open", (-104, 106), dict(tunnel=False, open_air=True)),
                     ("pandar360 open+train", (-180, 179.9), dict(tunnel=False, open_air=True, train_behind=True))]:
    d, ring = rays(*az)
    f, _ = frame(d, ring, *cast(d, **kw))
    print(f"{name:22s} original={orig(f.xyz)[0]} patched={patched(f.xyz)[0]}")
