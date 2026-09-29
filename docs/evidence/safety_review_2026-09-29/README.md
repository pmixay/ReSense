# Safety review of the three rules of 29.09 evening

> **Purpose:** the independent safety review (DETECTOR_FREEZE, step 3) of the three false-alarm rules that
> PR #29 switched on, its verdicts, the synthetic tests behind them and what was decided.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN · **Status:** dated record, 2026-09-29 night

## Scope

Commit `7532a6b` (`main`, seal `1e2ed82`): `tracking.explained_run` 5 (with `explained_reasons` column,
overhead, retro, shell), `cluster.shell_min_top` 2.3 m, `tracking.ego_veto_min_speed` 4 m/s. The review
read the diffs and the code, ran the three rules' test files (18 passed) and its own tests on the ray-cast
tunnel of `resense/synthetic.py` with the real `Detector` / `Tracker` and the default configuration. No
recording was used for the new tests, so **every number below is synthetic** (ray-cast tunnel, lidar
model of `resense/synthetic.py`). The scripts are in [`scripts/`](scripts) (`.py.txt`, run from the
repository root with the `.txt` removed); each sets the rules explicitly, so they still compare on / off
after the default changed.

## Verdicts

| rule | verdict | decision |
|---|---|---|
| `cluster.shell_min_top` 2.3 (shell attachment) | **BLOCKING** | **switched off** (`a5455b3`, the user's decision) |
| `tracking.explained_run` 5 | NON-BLOCKING, limits documented | kept |
| `tracking.ego_veto_min_speed` 4 m/s | NON-BLOCKING, limits and a documentation fix | kept; the launch file and README now say a constant `ego_speed_mps` must never be given |

Checks that hold for all three: a blocked or demoted track stays reported as `CAUTION` (every frame that
was `STOP` with a rule off was `STOP` or `CAUTION` with it on; none went silent); set O is unchanged by
them (0 of 407 gate keys differ against the `3eeb106` gate), and its objects are world-static (their
distance falls every frame), so the veto cannot touch them; neither set O nor set F has a floor-standing
object beyond 40 m that reaches the envelope top, so the gate could not see the shell regression.

## 1. Shell attachment — BLOCKING

Trigger (`resense/detector.py` `_shell`): a gauge cluster ≥ 40 m away, bottom below 0.8 m, top ≥ 2.3 m,
with ≥ 3 returns within 1.2 m above its top, the lowest within max(0.25 m, 3 vertical beam spacings).
Corridor candidates are clipped at the 3.0 m envelope top, so **any floor-standing object that continues
above 3.0 m supplies its own "lining"** and is demoted as infrastructure. Unlike the column rule, it has no
near-axis or width exemption for thin hanging objects (the organizers: broken hanging cables must be
detected, [`QA_session.md`](../../organizers/QA_session.md) fact 3).

First `STOP` distance, train approaching a static object (`scripts/shell_moving.py.txt`, reproduced by the
coordinator for the first two rows):

| object | 22 m/s: rule on / off | 10 m/s: rule on / off |
|---|---|---|
| catalogue `cable_low` (0.03 m cable down to 0.2 m above the rail head), on the axis | **21.0 m / 73.8 m** | 34.0 m / 116 m |
| 0.1 m pole, floor to vault, 0.3 m off the axis | **36.4 m / 104.6 m** | 44 m / 110 m |
| `cable_low`, 0.2 m off the axis | 29.8 m / 111.2 m | 36.0 m / 116 m |
| cable from the vault down to 0.1 m | never / 106.8 m | 39 m / 112 m |
| rear of a standing train (2.7 m wide, top 3.7 m) | 37.6 m / 121.2 m | 43.0 m / 126.0 m |

A static scene (`scripts/shell_probe.py.txt`, the documentation audit): a 10 × 2.6 m box 3.6 m tall on the
track at 60, 90 and 150 m is `CAUTION` with the rule on and `STOP` with it off; 3.1 m tall: `CAUTION` at
60 m; ≤ 2.9 m or 38–45 m: `STOP`. `explained_run` made it worse (every shell hit restarts its wait:
`cable_low` 36.4 m with shell alone, 21.0 m with both). A person, a person with raised arms and the 2 × 2 m
box at the envelope top (bottom 2.4 m) are not affected. Alone the rule bought ride events / `STOP`
episodes 32 / 31 → 31 / 29 ([gate table](../cycle_2026-09-29/competitor_rules/gate_table.md), `f_shell`).

## 2. `explained_run` — NON-BLOCKING

Trigger (`resense/tracking.py`): a track not yet in `STOP`, zone gauge, not near-escalated, with a hit
demoted as column / overhead / retro / shell among its last 10; it then needs 5 consecutive clean hits (a
miss restarts the count). In practice only column hits fire it now (`retro_intensity` is 0, overhead needs
the whole cluster above 3.0 m, shell is off). Measured (`scripts/expl_sim.py.txt`): a person merged with a
column for 10 frames who steps onto the axis — identical to the rule off (the existing `column_hold`
dominates); one column hit on a fresh track: +1 to +4 frames (≤ 0.4 s); with sparse returns a miss restarts
the run: worst case +8 to +10 frames (≤ 1.0 s, ≤ 22 m at 22 m/s).

## 3. Ego-motion veto — NON-BLOCKING

Trigger (`resense/tracking.py`): speed (median of the last five known) ≥ 4 m/s, track ≥ 25 m away, ≥ 4 hits
and ≥ 4 m of travel in the segment, Theil–Sen slope of distance against travel above −0.35; near escalation
(≤ 35 m) overrides it. Measured (`scripts/ego_*.py.txt`):

* static object, correct speed: identical to the rule off at 8 and 22 m/s; distance noise σ ≤ 1 m: 0 of 400
  runs changed; σ = 2 m: 4 of 400 delayed by ≤ 5 frames;
* an object moving away is vetoed above ~0.65 × train speed (at 22 m/s a vehicle receding at 15 m/s: `STOP`
  at 32.0 m instead of 127.2 m); when it stops, `STOP` follows in ~3 frames; objects approaching: never;
* standing or slow train with the LiDAR estimate (the default): no veto; the estimator gave no estimate
  ≥ 4 m/s on 641 standing frames and its p90 error on the recordings is 0.17–0.2 m/s;
* **a constant `ego_speed_mps` is the hazard**: with 22 m/s given on a standing train a person at 60 or
  100 m stays `CAUTION`; the default (−1: no given speed) is safe. The launch file's example suggested
  `ego_speed_mps:=22`; it now warns against it;
* not measured: a train passing on the adjacent track producing a spurious speed.

## Decision

The user switched the shell rule off on 29.09 night (`cluster.shell_min_top` 0, commit `a5455b3`) and kept
the other two with their limits documented (ALGORITHM, README). The full regression gate of the shell-off
commit and the new seal are in [`DETECTOR_FREEZE.md`](../../DETECTOR_FREEZE.md).
