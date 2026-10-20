"""T1 (P4 handoff 20.10): how close the real recordings' starts are to the L16/S3 open-air FAULT.

Runs an unmodified jury runner (``judge_runner_set.py`` for a bag, ``falcon_trace.py`` for Falcon) with
``--limit``, after wrapping two names read-only:

* ``MountCalibrator.update``: before the original runs, the cloud it is given (``xyz_cfg``, the configured
  vehicle frame: fastcloud decode, then ``R_vs``) is summarised: number of returns, share with z > 0 and
  with x < 0 over all returns, the same per-axis positive shares over ``directional_axes``' own sample
  (stride to <= 16384, |p| > 1 m: the numbers its 98 % test sees), and ``directional_axes(xyz_cfg)``
  (a pure function, called on its own). After the original returns: the calibrator's locked cue
  (``_forward_axis``), ``orientation_conflict`` and its message.
* ``directional_axes``: every call the calibrator itself makes, with its result.

Nothing the detector computes is changed; the runner's own ``.jsonl`` must equal a plain run's (checked by
the caller). Output: ``<out>.t1.json``.

    python t1_probe.py <out> <runner.py> <runner args ...>
"""
import json
import os
import runpy
import sys

import numpy as np

out, runner, args = sys.argv[1], sys.argv[2], sys.argv[3:]
ROOT = os.environ["RESENSE_REPO"]
sys.path.insert(0, ROOT)
import resense.calibration as cal  # noqa: E402

rows, calls = [], []
_orig_axes = cal.directional_axes
_orig_update = cal.MountCalibrator.update


def _v(a):
    return None if a is None else [float(x) for x in a]


def summary(xyz):
    x = np.asarray(xyz, np.float64)
    fin = np.isfinite(x).all(axis=1)
    x = x[fin]
    p = np.asarray(xyz)[::max(1, int(np.ceil(len(xyz) / 16384)))].astype(np.float64)
    ln = np.linalg.norm(p, axis=1)
    p = p[np.isfinite(p).all(axis=1) & (ln > 1.0)]
    f, u = _orig_axes(np.asarray(xyz))
    return {"n": int(len(x)), "z_pos": float(np.mean(x[:, 2] > 0)) if len(x) else None,
            "x_neg": float(np.mean(x[:, 0] < 0)) if len(x) else None,
            "sample_n": int(len(p)), "sample_pos": [float(v) for v in np.mean(p > 0, axis=0)] if len(p) else None,
            "cue_forward": _v(f), "cue_up": _v(u)}


def axes_hook(xyz):
    f, u = _orig_axes(xyz)
    calls.append({"frame": len(rows) - 1, "forward": _v(f), "up": _v(u)})
    return f, u


def update_hook(self, xyz_cfg, xyz_cur, track, periods=1, ring=None):
    r = summary(xyz_cfg)
    r["frame"] = len(rows)
    rows.append(r)
    res = _orig_update(self, xyz_cfg, xyz_cur, track, periods=periods, ring=ring)
    r["locked_forward"] = _v(self._forward_axis)
    r["orientation_conflict"] = bool(getattr(self.state, "orientation_conflict", False))
    r["message"] = self.state.message
    return res


cal.directional_axes = axes_hook
cal.MountCalibrator.update = update_hook
sys.argv = [runner] + args
try:
    runpy.run_path(runner, run_name="__main__")
except SystemExit:
    pass
json.dump({"runner": runner, "args": args, "frames": rows, "calibrator_calls": calls}, open(out + ".t1.json", "w"),
          indent=1)
print(f"{out}: {len(rows)} frames, {len(calls)} calibrator calls of directional_axes", file=sys.stderr)
