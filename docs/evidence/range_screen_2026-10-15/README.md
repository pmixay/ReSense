# R2/R1: preliminary configuration screen, 15.10

**Owner:** P3. **Measured code:** `264f5b2` on `p3/range-screen`, a
documentation-only continuation of `d0d17bb` (`final/silent-misses`).
**Verdict:** all five global configuration variants rejected by the full
regression gate. No screened variant is offered for the 1.2.0 bundle.

The variants and acceptance targets were committed before measurement in
[`protocol.json`](protocol.json). Every variant was tested separately on
the same data, without `--allow`. An unmodified full control reproduced the
published baseline first ([`baseline_gate.json`](baseline_gate.json)).

## Full gate results

Baseline: ride **27 events / 30 STOP episodes**, squareT platform **7 / 11**,
Set F trolley false detections **5**.

| variant | global override | exit | failing gated metrics |
|---|---|---:|---|
| R2a | `cluster.weak_min_points=3` | 1 | ride events 27 -> 28; episodes 30 -> 31 |
| R2b | `cluster.far_range=60` | 1 | ride events 27 -> 31, episodes 30 -> 33; squareT platform events 7 -> 9, episodes 11 -> 13; Set F trolley false detections 5 -> 6 |
| R1a | `tracking.low_confirm_hits=3` | 1 | ride events 27 -> 30 |
| R1b | `lowobj.straddle_min_width=0.25` | 1 | ride events 27 -> 28 |
| R1c | `lowobj.range_max=75` | 1 | ride events 27 -> 30; episodes 30 -> 33 |

Full reports: [`gate_R2a.json`](gate_R2a.json), [`gate_R2b.json`](gate_R2b.json),
[`gate_R1a.json`](gate_R1a.json), [`gate_R1b.json`](gate_R1b.json),
[`gate_R1c.json`](gate_R1c.json); process exits: [`gate_exits.json`](gate_exits.json).
All reports include the six recordings, Set O, all eight ride pieces and
Set F. A passing Set O subset alone was not treated as a passing gate.

## Range and Set O screen

All codes use the same node-decoded A background, sealed baseline axis,
recomputed ICP, object placement and noise seeds. Range windows:
`--start 150 --d0 230 --end 340`.

| object / variant | first matching STOP, m | held-from, m | matching STOP frames |
|---|---:|---:|---:|
| A cube 0.5 m, control | 135.06 | 83.37 | 66 |
| A cube 0.5 m, R2a | 135.06 | 87.69 | 69 |
| A cube 0.5 m, R2b | 135.06 | 87.69 | 69 |
| A cube 0.3 m, control | 44.86 | 49.32 | 29 |
| A cube 0.3 m, each of R1a/R1b/R1c | 44.86 | 49.32 | 29 |

[`range_probes.json`](range_probes.json) is the measured source. The 0.3 m
control's first/held distances and 30-60 m bin (11/21) reproduce the backlog;
this run records **29** total matching frames (18 below 30 m + 11 at 30-60 m),
without silently replacing it by a quoted older total.

Set O ([`set_O_screen.json`](set_O_screen.json)): all five variants have zero
failing Set O rows. R2b alone improves small_center first STOP **55.8 -> 59.2 m**,
small_on_rail **42.7 -> 44.4 m**, and inside STOP frames **411 -> 414**.
The other four are unchanged on these objects. None reaches R2's held-range
target of 120 m or small_center target of 65 m; the R1 variants do not reach
the 55/52 m first/held targets. The full false-alarm regressions independently
reject all five even where a range metric improved.

## Scope and next step

These are the cheap **global** overrides registered for screening. In R1a
and R1b, the later conditional code proposals (top reaching `min_top`, length
<=0.6 m) still require their own acceptance, measurement and gate. The
hardware-rule change and R2's monotone/floor-verified code paths have not
been evaluated by this screen.

P4's **X1 attribution** is the next input: identify the first failing rule or
tracker hold before choosing another code candidate. Re-check any future
candidate after rebasing onto the 1.1.0 seal. These probes are development
data; they provide no held-out/G3 claim.

Environment and exact gate commands: [`provenance.json`](provenance.json).
Shared data intake, retained raw-output identities and the scratch drivers:
`docs/evidence/p3_start_2026-10-15/` on this branch.
