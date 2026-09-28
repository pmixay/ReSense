# How it works

The idea: do not try to recognise objects. Describe the normal tunnel from the data in every frame,
cut out the space the train will sweep, and report whatever persistently occupies it. There is no
map: the tunnel model is rebuilt from each frame.

```text
PointCloud2 (10 Hz) ──▶ resense_ros/detector_node ──▶ resense.Detector.process(frame)
  1. sensor → vehicle frame (X forward, Y left, Z up), range crop          frame.py
  1b. mount auto-calibration: orientation, roll, pitch from rails and bed  calibration.py
  2. track model: bed profile, rail heads, track axis, curvature from walls track.py
  3. clearance-envelope corridor along the axis (2.1 × 3.0 m + advisory)    gauge.py
  3a. low objects on the rails                                             lowobj.py
  3b. multi-frame accumulation beyond 40 m (only with a known speed)       accumulate.py
  4. voxels → range-adaptive DBSCAN → infrastructure filters               clustering.py
  5. persistence tracker → confirmed tracks                                tracking.py
  5b. health: input, visibility, rail lock, monitored range                health.py
  6. FrameResult → decision, distances, JSON, markers                      detector_node.py
```

## 1. Where the sensor is

The LiDAR is not in the same place on every train. The detector maps the sensor's axes to the
vehicle frame (configurable) and, by default, calibrates the mount itself from the first frames:
the rail pair gives the orientation and roll, the bed slope gives the pitch. The result is reported
in the status JSON under `mount`.

## 2. The track model

Per frame: the bed height along the track (robust per-bin fit), the rail-head level and the track
centre and yaw from a two-rail template (1.52 m gauge), and the curvature from the left and right
tunnel boundaries (walls, column rows). The axis is trusted only as far as the boundaries are
actually observed; beyond that, objects can only be advisory.

## 3. The envelope

The organizers' train envelope, 2.1 m wide and 3.0 m tall above the rail head, is swept along the
fitted axis. A band 0.35 m wider is the advisory zone. Near the train, on straight track, the
envelope is the union of the one built from the rails and the one measured from the sensor axis,
so neither side is narrowed. Nothing lying on the bed below the envelope floor between the rails
is reported (the organizers confirmed such an object is not an obstacle); objects on a rail, or
straddling the floor, are found by a separate low-object stage.

## 4. Candidates and infrastructure

Points inside the corridor are voxelised and clustered with DBSCAN whose radius grows with range.
Tunnel hardware that legitimately comes close to the envelope — thin linear fixtures, low track
hardware, wall faces, columns, overhead ducts — is recognised by shape signatures and demoted to
advisory, never deleted from the output. Thin objects hanging near the axis (a broken cable) are
never demoted.

## 5. Persistence and the decision

A cluster becomes a track; a track becomes an obstacle only when it is **confirmed**: seen in at
least 3 frames over at least 0.5 s, matched in most of its recent frames, with enough confidence,
and inside the strict envelope in most of its recent hits. A reported obstacle is held over one
missed frame. A small learned model (gradient-boosted trees) may delay a doubtful far STOP by a
bounded number of frames in a track's life — never within 25 m, never for a standing body within
40 m, and it can never veto or remove a STOP.

The decision per frame:

* `STOP` — a confirmed track inside the envelope;
* `CAUTION` — only advisory tracks, known infrastructure, degraded health or catching up;
* `GO` — none of the above;
* `FAULT` — no input, stale input, or untrusted clocks (a held STOP takes priority).

## 6. Health and the monitored range

Every frame also reports how far the track is actually being watched (`clear_distance`): the
sightline and the trusted track-model range, capped at any detected obstacle or eligible cluster.
It is an estimate, not a guarantee that the track is empty.

## Performance

One CPU core per node, no GPU. On the organizers' recordings a frame typically takes a fraction of
the sensor's 100 ms period; dense station scenes are the slowest and can exceed it. Optional C++
kernels (built into the image) cut the detector time by about half with bit-identical output. Measured timings with their dates and machines: README “Headline results” and
[`docs/EXPERIMENTS.md`](https://github.com/pmixay/ReSense/blob/main/docs/EXPERIMENTS.md) §3.

## Read more

* [`docs/ARCHITECTURE.md`](https://github.com/pmixay/ReSense/blob/main/docs/ARCHITECTURE.md) —
  components, data flow, real-time budget, deployment without internet
* [`docs/ALGORITHM.md`](https://github.com/pmixay/ReSense/blob/main/docs/ALGORITHM.md) — every
  stage, the decision rule, parameters, limitations
* [`docs/EXPERIMENTS.md`](https://github.com/pmixay/ReSense/blob/main/docs/EXPERIMENTS.md) — every
  measurement, including the approaches that did not work
* [`docs/DECISIONS.md`](https://github.com/pmixay/ReSense/blob/main/docs/DECISIONS.md) — key
  decisions: hypothesis → experiment → result
