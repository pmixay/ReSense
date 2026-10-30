#!/usr/bin/env python3
"""Does the K2 curve pass (Detector._curve_clusters) leave any detector state changed other than its
own trace fields?  Wraps the method: a deep fingerprint (pickle, sha1) of every attribute of the
detector -- and of the nested objects it owns (tracker, health, far tracker, buffer, calib ...) --
before and after each call; any attribute whose fingerprint differs, other than the clusters list it
returns and its trace fields (_curve_added, _curve_seen), is written to PROBE_OUT as a leak.

Positive control (PROBE_CONTROL=1): the wrapper itself sets det._far_report_cap = 1.0 inside the call
(after the original returns) -- the probe must report that field on every curve frame.

    PROBE_OUT=leaks.jsonl python curve_state_probe.py <script.py> [args...]   # runs the script as __main__
"""
import hashlib, json, os, pickle, runpy, sys

R = os.environ["RESENSE_REPO"]
for p in (R, R + "/scripts", R + "/ros2_ws/src/resense_ros"):
    sys.path.insert(0, p)
import resense.detector as D  # noqa: E402

OUT = open(os.environ["PROBE_OUT"], "a")
CONTROL = os.environ.get("PROBE_CONTROL") == "1"
EXPECT = {"_curve_added", "_curve_seen"}
orig = D.Detector._curve_clusters
stats = {"calls": 0, "leak_calls": 0, "added_calls": 0}


def fp(v):
    try:
        return hashlib.sha1(pickle.dumps(v, protocol=4)).hexdigest()
    except Exception as e:  # unpicklable: identity and repr
        return f"id{id(v)}:{type(v).__name__}:{e.__class__.__name__}:{hashlib.sha1(repr(v).encode()).hexdigest()}"


def snap(det):
    return {k: fp(v) for k, v in vars(det).items() if k not in EXPECT}


def wrapped(self, xyz, intensity, clusters, base_valid=0.0):
    before = snap(self)
    out = orig(self, xyz, intensity, clusters, base_valid)
    after = snap(self)
    keys = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    stats["calls"] += 1
    stats["added_calls"] += int(getattr(self, "_curve_added", 0) > 0)
    if keys:
        stats["leak_calls"] += 1
        OUT.write(json.dumps({"call": stats["calls"], "keys": keys, "added": getattr(self, "_curve_added", None),
                              "far": self._far_axis is not None}) + "\n")
        OUT.flush()
    return out


def wrapped_control(self, xyz, intensity, clusters, base_valid=0.0):
    before = snap(self)
    out = orig(self, xyz, intensity, clusters, base_valid)
    saved = self._far_report_cap
    self._far_report_cap = 1.0               # planted leak
    after = snap(self)
    self._far_report_cap = saved             # undo, so the run itself is unchanged
    keys = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    stats["calls"] += 1
    if keys:
        stats["leak_calls"] += 1
        OUT.write(json.dumps({"call": stats["calls"], "keys": keys, "control": True}) + "\n")
    return out


D.Detector._curve_clusters = wrapped_control if CONTROL else wrapped
import atexit  # noqa: E402
atexit.register(lambda: (OUT.write(json.dumps({"summary": stats, "control": CONTROL}) + "\n"), OUT.flush()))
script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
