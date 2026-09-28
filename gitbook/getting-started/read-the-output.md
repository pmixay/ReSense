# Read the output

## The decision

| `/resense/decision` | meaning |
|---|---|
| `STOP` | **alarm**: a confirmed obstacle inside the organizers' 2.1 × 3.0 m train envelope |
| `CAUTION` | advisory, **not an alarm**: a confirmed object just outside the envelope, a far cluster beyond the trusted track-model range, known infrastructure, degraded health, or the node catching up after a stall. Common in an ordinary tunnel |
| `GO` | no obstacle detected and no health warning that affects the decision |
| `FAULT` | no input (before the first frame, or more than 0.5 s without frames) or input that cannot be trusted |

`GO` is a detection result, **not** permission to move a train.

## What to evaluate

| question | topic | type | values |
|---|---|---|---|
| is there an obstacle? | **`/resense/decision`** | `std_msgs/String` | `STOP` = alarm |
| the same as a boolean | `/resense/obstacle_detected` | `std_msgs/Bool` | confirmed over 0.5 s, held over one missed frame |
| how far is it? | **`/resense/nearest_distance`** | `std_msgs/Float32` | m along the track, −1 if none |
| how far is the track monitored? | `/resense/clear_distance` | `std_msgs/Float32` | estimated monitored range, m; 0 on a fault |
| is the input healthy? | `/resense/health` | `diagnostic_msgs/DiagnosticArray` | OK / WARN / ERROR / STALE with values |
| everything | `/resense/status` | `std_msgs/String` (JSON) | [Topics and status JSON](../reference/topics.md) |

`clear_distance` is an estimate from the sightline and the trusted track model, capped at detected
obstacles and eligible clusters. An object that forms no such cluster can still be inside that
range. Read `STOP` and `nearest_distance` together with health and warnings.

## A typical run on a recording with an obstacle

```text
FAULT     # before the first frame arrives (the player is still loading the bag)
GO        # first frames
CAUTION   # an object approaches the envelope from the side
STOP      # a person on the track, then an object on the rail; nearest_distance ≈ 55–57 m
FAULT     # 0.5 s after the bag ends: no input, the path is not monitored
```

This is the shape of the output on the organizers' `doubleT_obstacle` recording; exact frames and
distances depend on the machine and are recorded in `docs/EXPERIMENTS.md`.

## Freshness: using the output in software

For an automatic consumer `/resense/decision` alone is not enough: a latched string carries no age.

* Read `/resense/status` and its `freshness` object: the clocks used, ages, `valid`, a `reason`,
  and `go_allowed` (true only for a GO that is valid at evaluation time).
* `evaluated_at_utc_s`, `max_result_age_s` (0.5 s) and `future_tolerance_s` (0.05 s) let you expire
  a result with your own timer; that assumes synchronized UTC clocks.
* When input stops or processing fails, every output reports invalid monitoring. A previous `STOP`
  stays visible with `stop_held: true`, its original stamp and a zero monitored range, until a
  fresh valid non-STOP frame clears it. Without a previous STOP the decision is `FAULT`.
* Watchdog and error snapshots carry `snapshot_kind: watchdog | processing_error`; processed
  frames carry `snapshot_kind: frame`.

The full contract: README
[“Topics published by the node”](https://github.com/pmixay/ReSense/blob/main/README.md#topics-published-by-the-node).

## Offline, without ROS

`resense run --bag <dir> --out results.jsonl` writes the same per-frame JSON as `/resense/status`
(one object per line) — see [Offline analysis without ROS](../guides/offline-analysis.md). Such a
file, or a capture of `/resense/status`, can be replayed in the
[web dashboard](../visualisation/web-dashboard.md).
