import numpy as np
from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
from resense.config import SensorConfig
from resense.frame import axis_matrix
r = axis_matrix(SensorConfig())
scenes = {}
for name, specs in [('clear', []), ('obstacle', [ObstacleSpec(kind='box', size=(0.6,0.6,0.6), distance=40.0)])]:
    f, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(3), specs=specs)
    scenes[name] = (f.xyz @ r).astype(np.float32)
np.savez('/home/resense/validation/quality_cycle/freshness/scenes.npz', **scenes)
