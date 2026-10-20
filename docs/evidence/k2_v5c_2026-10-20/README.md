# K2 v5c: keep genuine detections beyond the reach cap (20.10)

> **Owner:** P4 (author; the review is by P3 or a fresh agent) · **Decides:** the captain · **Status:** measured on the
> data (20.10, §6–§7) on `main` `8c2bf51`; every switch stays **off** by default. Registered rows: **G-1 pass, ID pass,
> K1-2 reported; F-1 fail as scored** (every extra STOP is on the person; the scorer's reading, §6), **M-1 fail** (the
> tunnels cube, as predicted; at 30 m also a platform cube). G-2 (X3): see §6. T3 (§7): K2 does not bend away from the
> tunnels cube; the cube is an edge object that K2-off's displaced axis carries into its gauge. G3 not touched.
> Package this answers: [`../k1_k2_gauge_2026-10-19/P4_PACKAGE.md`](../k1_k2_gauge_2026-10-19/P4_PACKAGE.md) §3 row 0.

## 1. Correction: variant B cost the Falcon person 2.6 m, not 12 m

DECISIONS row 44 held K2 off because the walking person on the Falcon recording was "first stopped at 113.0 m instead
of 124.8 m, 158 of 1,360 STOP frames lost". Both numbers come from
[`score_falcon.py`](../integration_2026-10-19/scripts/score_falcon.py). That scorer counts a base STOP as kept only when
the candidate has a STOP detection within 0.5 m in distance **and in lateral**. The lateral is measured from each run's
own axis, and K2 changes the axis: the same person, at the same place in the vehicle frame, is 0.06 m from K2's axis
and 0.89 m from the base axis (frame 2994). The scorer therefore counted most of K2's STOPs on the person as lost.

Re-scored from the committed per-frame records (`runs/falcon_final_11bb1ab.jsonl.xz` vs `runs/falcon_k2B_c9e8daa.jsonl.xz`):

| row | `score_falcon.py` (lateral match) | decision level / vehicle-frame match |
|---|---|---|
| first STOP on the person | 124.84 → **112.97 m** (frame 2972 → 3070) | 124.84 → **122.27 m** (frame 2972 → 2994) |
| person STOP frames lost (of 1,360) | 158 | **37** without any STOP (36 at 113–125 m, the person beyond the cap; 1 at 5.7 m, frame 4382); 23 more where K2 STOPs at the person's place (vehicle Y −0.05 to 0.17 m; cluster 0.7–1.9 m wide, 20 of 23 ≤ 1.05 m) while base's cluster is a 2.0–2.7 m wide merge whose centre is > 0.5 m away ([`scripts/score_falcon_pos.py`](scripts/score_falcon_pos.py): 60) |
| new STOP frames, false STOPs | 9 new (4373–4379, 4410–4411), 0 of the 4 attributed false | unchanged |

Checks: frame 2994 printed in both runs (A: 122.27 m, vehicle (122.44, 0.12), lateral −0.89; B: 122.27 m, vehicle
(122.44, 0.12), lateral 0.06). Over 243 frames in 2972–3300 where both runs STOP within 0.5 m in distance, the
vehicle-frame Y differs by at most 0.63 m while the lateral differs by median 0.39 m (p90 0.76 m). Positive control:
both scorers give 0 lost for the base run against itself. The 23 cluster-shape frames were listed one by one (all at
100–118 m, the same person). Base puts the person 0.6–1.0 m from its axis, near the gauge edge (core half-width 0.87 m
at 120 m), and K2 within 0.3 m of its axis. That K2's axis is the truer one there is **inferred**, not verified (no
independent track reference for Falcon).

What remains real: 36 STOP frames lost at 113–125 m (plus frame 4382 at 5.7 m, not attributed) and the first STOP
2.6 m later. In those 36 frames, matching variant B's warnings to the base STOP by vehicle position (within 1.5 m
in distance and 0.7 m in Y), the person is a warning `beyond_axis` in 15 (all 1.2–13.7 m beyond the monitored range:
the reach cap), `beyond_height_ref` in 2, a warning with no reason in 14 (inside the monitored range; the tracker had
not confirmed it, inferred to follow the demotions) and not reported at all in 5. Only the 15 `beyond_axis` frames are
what the reach cap does directly. (A first, looser count on 20.10 morning gave 19 / 2 / 15; it matched the first
warning near the person and is superseded.)

## 1b. A second genuine loss, inside the cap: v5c does not address it (added 20.10, after revision 1)

The integration evidence also records that variant B STOPs the **small cube right of `synthetic_tunnels`** (marker id
19) in fewer frames, and calls it "probably just outside the 2.1 m gauge; not verified". Scored per marked object from
the committed records ([`../n5_markers_2026-10-20/`](../n5_markers_2026-10-20/README.md)): it is the only marked object
that loses STOPs under B, **29 → 13 frames, first STOP 55.0 → 27.6 m** (frames 259–273 and 279 lost). It is inside the
gauge: a static object keeps its offset from the track, and measured from 1.1.0's axis its centre is 0.96 m right of
the axis (median) both inside the rails' range and at 30–55 m, K2's axis giving the same inside the rails' range; its
inner face is about 0.7 m from the axis, 0.3 m inside the half-width. At 30–55 m B's monitored range is 67–87 m, so
the loss is **inside the trusted range**: the cube touches B's strict envelope in 9 of 15 frames (the clear distance is
capped at it) and is never confirmed. B's joint axis there is about 0.3 m farther from the cube than the true axis
(inferred; the records have no axis at the cube for B). Set O `small_center` (§6) is the same kind of loss, at 55 m.

v5c changes nothing before the cap, so it **does not restore this cube**. Making the rule an OR of the two gauges
inside the cap would, but the committed gate rows show variant B (with K1, `gatework_v5b`) also removing strict
detections at 30–60 m on the ride, where the gate counts every STOP as a false alarm: 10 of them with the joint axis
0.3–0.6 m farther out than base's (`new_data_4` 1223–1228, `new_data_7` 623–624 and 643–644), which such a rule would
bring back ([`../n5_markers_2026-10-20/scripts/k2_removed.py`](../n5_markers_2026-10-20/scripts/k2_removed.py)). What makes the joint fit bend wrongly in the
tunnel needs the cloud (frames 255–275); this container cannot reach it. Until then **K2 is not ready to switch on**,
v5c included.

**Superseded by §7 (data run, 20.10):** measured against the rails, the cube's centre is 1.165 m from the axis (inner
face 0.92 m, 0.05–0.08 m inside the strict envelope), and over frames 259–273 B's axis is nearer the true axis than
K2-off's, both displaced towards the cube. The 0.96 m above was measured from 1.1.0's axis.

## 2. v5c: what both axes put in the gauge stays an obstacle

**Switch:** `track.axis_joint_reach_dual` (m, default **0.0 = off = v5b**), in `resense/config.py` and both YAMLs.

With the reach cap on, the cap is where the walls stop confirming the joint shape. v5b ends the trusted range there,
so everything beyond becomes advisory, true objects included. v5c moves that end out by `axis_joint_reach_dual`
metres (never past the base estimator's own range), on frames the cap shortened only. An obstacle whose nearest point
lies between the cap (`track.joint_reach`) and that end stays an obstacle only when its lateral extent (its box,
accumulated points included, at its centroid's distance) also reaches into the strict gauge measured from the base
axis; otherwise it is advisory `beyond_axis`, exactly as v5b makes it (`Detector._dual_zone`, run right after
clustering). A cluster that starts before the cap is not touched, so nothing v5b keeps as an obstacle is demoted.
Everything else is v5b.

**Revision 1 (20.10, before any measurement).** The first version (commit `a246bf0`) ANDed the two memberships per
point before clustering. The self-review found two flaws: a cluster starting before the cap with its strict points
only beyond it could lose its STOP compared with v5b, and the accumulated points of earlier frames (accumulation is
on beyond 40 m, 5 frames) were not held to the rule. The rule moved to the cluster level, and the range and
`axis_valid_both` / `_bent` are extended only on frames the cap shortened.

Why this targets the genuine detections and not the false ones: the base axis is trusted that far without K2, so an
object inside both gauges is one that neither shape can explain away. The two false alarms v5b's cap was traced to
remove ([`V5.md`](../k1_k2_gauge_2026-10-19/V5.md) §6) lie inside only one: roundT_doubleT frames 96–99 (base axis
5.2 m off the driven path, the cluster 1.6 m from it) and set O background 661–665 (base and joint axes 1.3 m apart at
118 m, on opposite sides).

Code: `resense/track.py` `_joint_output` (the extended range), `resense/detector.py` `_dual_zone` (the rule).
Tests (`tests/test_k1_k2_axis.py`, 3 new): 0 is v5b bit for bit and the range never passes base's; beyond the cap a
cluster inside both gauges, or spanning the base axis, stays an obstacle, one inside the joint gauge only or past the
base gauge's edge is demoted, one starting before the cap, an already advisory one and every cluster on an uncapped
frame are left alone; `Detector.process` runs the rule only with the switch on. Mutation checks: removing the demotion
or testing the adjusted distance instead of the nearest point fails the rule test; dropping the extension fails the
range test. `tests/test_k1_k2_axis.py` 24 passed. Off identity on synthetic scenes
([`scripts/synthetic_identity.py`](scripts/synthetic_identity.py): the entry-curve scene at three curvatures with a
person at 60–158 m or none, and the station scene with a person at 25–83 m; 18 scenes × 10 frames, every field of the
result and the track): this branch equals `main` (`0acb18c`) with K2 off (0 of 180 rows differ) and with variant B
(0 of 180); v5c-15 differs from variant B in 101 rows, all in the track range and the clear distance, none in a
decision, detection or warning (in these scenes the base axis is 3.6–5 m off the track beyond the cap, so v5c keeps
v5b's demotions); positive control: variant B differs from off in 180 rows, 66 of them in decisions or detections. Full suite in this container (revision 1): 1,897 passed, 190 skipped,
25 failed and 2 errors; the same 27 fail on `main` (`0acb18c`, run with its own checkout first on the path), from
modules missing here (`open3d` for the synthetic injection and others), not from this change.

## 3. Offline proxy (not a measurement)

[`scripts/dual_proxy.py`](scripts/dual_proxy.py) reads the committed gate rows of base (`aec88d2`, F1's
`gate_frames_base_cand.tar.xz`) and of v5b (`../k1_k2_gauge_2026-10-19/results/v5/raw_v5.tar.xz`, `gatework_v5b`). It
lists every base STOP-zone detection beyond v5b's cap that v5c would keep strict (inside the extended range and inside
the gauge from v5b's joint axis). Limits: it ignores the tracker, and that v5b run has K1 on and is on `b2c523a`, not
variant B on the current commit.

| recording | base STOP-zone detections beyond v5b's cap | v5c keeps (15 m) | what |
|---|---|---|---|
| set O (`cloud_with_fake_obj`) | 1 | 1 | frame 175, 46.7 m, 1.96 × 1.94 m object (v5b STOPs that frame anyway) |
| ride `new_data_4` | 4 | 2 | frames 265–266, 28.7 m, 0.06 m high (cap at 23 m) |
| ride `new_data_5` | 7 | 5 | frames 899–906, 97–103 m, 2.8 × 1.5 × 1.6 m structure at the gauge edge |
| ride `new_data_6` | 14 | 1 | frame 814, 104.5 m, single frame |
| squareT_platform (the 147 m structure), five empty recordings, every other | 8 / 0 | **0** | — |

So the proxy expects at most **3 of the 18 ride episodes** that variant B removed to come back (ride STOP episodes
9 → at most 12; without K2: 24), the squareT_platform and empty-recording gains to stay, and no change on set O's
STOP frames. On Falcon, of the 36 lost frames the 15 `beyond_axis` ones are what v5c changes directly: the person's
box reaches into the base gauge in every one of the 36 (base lateral −1.02 to 0.02 m, |lateral| − half width ≤ 0.73 m,
core 0.87 m) and its joint lateral is 0.0–0.45 m, and those 15 lie 1.2–13.7 m beyond the monitored range, so within
15 m of the cap if the monitored range equals the cap there (inferred; the monitored range is also limited by the
visibility and the wall drift). The 14 unconfirmed frames may follow once the demotions stop (inferred); the 2
`beyond_height_ref` and the 5 unreported ones are not touched by v5c. With 30 m the proxy adds one frame on
`new_data_5` and one on `new_data_6`.

## 4. Registered before measuring (rows, values, criteria; revision 2 of 20.10, still before any measurement)

Candidate **v5c-15** = variant B + `axis_joint_reach_dual: 15.0`; fallback **v5c-30** (30.0) only if F-1 fails at 15.
No other value is tried. Reference: the committed defaults of the measured commit (K2 off), as in the integration
evidence.

| # | row | criterion |
|---|---|---|
| F-1 | Falcon, whole recording, [`score_falcon_pos.py`](scripts/score_falcon_pos.py) | person first STOP ≥ 124.0 m; `n_person_no_stop` (decision level) ≤ 22 (variant B's 37 minus its 15 `beyond_axis` frames; the count is reported, fewer is better); no new STOP frame beyond variant B's 9 |
| G-1 | full gate, seal baseline, no `--allow` | the only failing rows are set O `small_center` (variant B's accepted exception); ride STOP episodes ≤ 12; five empty recordings and squareT_platform 0 episodes |
| G-2 | X3 battery vs the committed reference | not worse than variant B |
| K1-2 | standing person at 150 m (`S_person_150`) | reported (v5b 0 / 260, base 90 / 259) |
| ID | every switch off vs the commit without this change | identical per frame (gate and Falcon) |
| M-1 | the three marked synthetic bags, per marked object ([`per_object.py`](../n5_markers_2026-10-20/scripts/per_object.py) against the K2-off run) | every object's STOP frames and first STOP not worse than K2 off. Registered prediction: **fails** on the tunnels cube (id 19, as variant B: 29 → 13), because that loss is inside the cap (§1b). Added in revision 2 |

## 5. Commands (need the data; `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=<tree>`)

```bash
V="track.axis_joint_fit=true track.axis_joint_range=false track.axis_joint_min_curvature=0.0001 track.axis_joint_reach_cap=true track.axis_joint_reach_dual=15.0"
# G-1 (about 15 min with --jobs 2)
python scripts/regression_gate.py --cache <gate caches> --jobs 2 \
  --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json \
  --out <out>/gate_v5c.json --work <out>/work_v5c $(for s in $V; do echo --set $s; done)
python docs/evidence/integration_2026-10-19/scripts/cmp_frames.py <work K2 off> <out>/work_v5c
# F-1
python docs/evidence/f1_false_alarms_2026-10-19/scripts/falcon_trace.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ \
  --out <out>/falcon_v5c $(for s in $V; do echo --set $s; done)
python docs/evidence/k2_v5c_2026-10-20/scripts/score_falcon_pos.py <K2-off falcon .jsonl> <out>/falcon_v5c.jsonl
# K1-2 probe
F1_SET="$(echo $V | tr ' ' ';')" python docs/evidence/f1_false_alarms_2026-10-19/scripts/measure_probe.py \
  <decoded squareT_platform> <icp json> <out>/probe_v5c --obj 0.5,0.5,1.75 --start 360 --d0 150 --end 620
# proxy (no data needed)
python docs/evidence/k2_v5c_2026-10-20/scripts/dual_proxy.py <base gate work> <v5b gate work> 15
```

## 6. The registered measurement (20.10, data run; §4 revision 2, nothing else tried)

**Measured commit: `main` `8c2bf51`** (PR #43 squash-merged during the run; it carries this branch's switch and P3's later
H1 / R3 changes). Reference: the same commit with every K2 switch off. ID: the same commit against its parent `a5b0ede`.
Runs that had already been made on the branch head `972d19a` (Falcon K2 off / v5c-15, the marked bags) are kept as
checks: their K2-off Falcon equals the committed `4cf8e27` record in all 4,443 rows, and every number below that was
measured on both commits is the same on both. Environment: Python 3.12, numpy 1.26.4, scipy 1.13.1, scikit-learn
1.5.2, open3d 0.20.0, native kernels, `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`; every archive checked against the
sha256 the Yandex API publishes (Drive zip against `scripts/cold_bags.sha256`). Per-frame outputs:
[`runs/data_8c2bf51/`](runs/data_8c2bf51/).

| # | criterion | v5c-15 | v5c-30 (run because F-1 failed at 15) |
|---|---|---|---|
| F-1 | person first STOP ≥ 124.0 m; `n_person_no_stop` ≤ 22; no new STOP frame beyond variant B's 9 | **fail as scored**: first STOP 122.27 m (frame 2994); `n_person_no_stop` **10** (pass); new STOP frames 18 = B's 9 + 9 more (2979–2983, 3003, 3007, 3008, 3039) | **fail as scored**: 122.27 m; 10; 26 = B's 9 + 17 (also 2950–2957) |
| G-1 | only set O `small_center` fails; ride STOP episodes ≤ 12; five empty and squareT_platform 0 episodes | **pass**: exit 1 on the 6 `small_center` rows only (first STOP 55.8 → 52.5 m, held from 60.8 → 57.5 m, STOP frames 32 → 30), 11 rows better; ride STOP episodes 24 → **10** (alarm events 18 → 8); five empty 11 → **0**; squareT_platform 11 → **0** | **pass**: the same numbers as v5c-15 |
| G-2 | X3 not worse than variant B | running | not run |
| K1-2 | standing person at 150 m: reported | 0 / 259 STOP frames (K2 off 90 / 259; B 0 / 259) | 0 / 259 |
| ID | every switch off vs the commit without this change | Falcon: `8c2bf51` = `a5b0ede` in all 4,443 rows; gate: `8c2bf51` = `a5b0ede` in all 15,269 rows (36 differ in the latency health level only), set F equal; control: K2 off vs v5c-15 differ in every row | |
| M-1 | every marked object's STOP frames and first STOP not worse than K2 off | **fail**, as predicted: only the tunnels cube (id 19) 29 → 13 STOP frames, first STOP 55.0 → 27.6 m; every other object equal or better (switch cubes 12 / 13 / 0: 11 → 21, 4 → 9, 35 → 37; tunnels big cube 52 → 55; platform cube 23 38 → 40) | **fail**: the tunnels cube as at 15, **and** the platform's small cube right (id 23) 38 → 31 STOP frames, first STOP 86.8 → 76.4 m |

**F-1, what the scorer counts.** [`score_falcon_pos.py`](scripts/score_falcon_pos.py) counts a candidate STOP only in
the reference's own STOP frames (`first_person_stop_cand` is the first *kept* one) and every other STOP frame as new.
All 9 extra frames of v5c-15 and all 17 of v5c-30 are STOPs on the walking person: vehicle Y 0.04–0.16 m, at the
person's distance in the frame (127.2 → 116.8 m), where K2 off has the same person as a warning (`beyond_axis` or
unconfirmed) and variant B's committed record (`c9e8daa`) a `beyond_axis` warning in every one of them but 2956
(unconfirmed). Counted as the person, v5c-15's first STOP is frame 2979 at **124.02 m** and v5c-30's
frame 2950 at **127.18 m** (K2 off 124.84 m). So as registered F-1 fails at both values; read by position it would pass
at both (v5c-15 by 0.02 m). That reading was not registered, and the decision is the captain's. The scorer's output
had lost its `new_stop_frames` / `n_new_stop` keys (they sat inside a comment); fixed before scoring, and the committed
base vs variant B records reproduce §1 exactly (37 / 122.27 m / 9 new: 4373–4379, 4410–4411).

**M-1 at 30 m, the platform cube.** In frames 103–112 (cube at 90.6–79.0 m) v5c-30's track of the cube carries the
tracker's `doubt` reason and stays a warning; K2 off STOPs from 106 (86.8 m), v5c-15 and B from 104. Inferred, not traced: the
wider dual zone demoted a hit of that track and the doubt held it for 10 frames. v5c-30 is therefore worse than v5c-15 on a marked
object; the tunnels cube is the same at both values (and in B).

**K1-2.** `measure_probe.py` on the node-decoded squareT cache with the ICP odometry regenerated here (open3d 0.20.0;
not byte-identical to the committed hash, which the range-attribution README says open3d never is run to run): the
object's per-frame position X and Y equal the committed 1.1.0 attribution rows in all 259 frames, and K2 off reproduces
the registered 90 / 259.

## 7. T3: why K2 loses the tunnels cube (marker 19), measured on the cloud (20.10, data run)

**K2 does not bend away from the cube; the cube is an edge object, and it is K2-off's axis that is displaced, towards
it.** Measured against the rails, the cube's centre is **1.165 m** right of the track axis, not the 0.96 m of §1b and
the n5 README (that figure was measured from 1.1.0's own axis, which near the cube runs 0.18–0.31 m right of the
rails). Its inner face is **0.92 m** from the axis, and the strict envelope at 30–55 m reaches 0.97–1.00 m, so the cube
is inside it by only 0.05–0.08 m. Over the 15 lost frames (259–273) **both** axes sit right of the true axis, towards
the cube: K2-off by 0.08–0.37 m (median 0.21), variant B by −0.22…+0.06 m (median 0.11). K2-off STOPs on the cube from
55 m because its axis error carries the cube 0.2–0.4 m deeper into its gauge; B's nearer-true axis leaves the cube's few
returns at the edge.

So there is no K2 error here for a rule to correct, and none was registered or implemented. An OR of the two gauges
inside the cap would restore these STOPs only by trusting the more displaced axis.

**The true axis.** The cube is static, so its offset from the track is the same at every distance. In frames 275–284
(cube 9.5–26.5 m ahead) the rail-head returns in front of it (|h| < 0.06 m; 4 m to the near face − 0.5 m, where the
cube does not shadow the right rail) were split into the two rails by their lateral from the K2-off axis (0.45–1.15 m,
selection only), each rail fitted as a robust line in absolute Y, and the midpoint taken at the cube's near face
([`scripts/t3_rails.py`](scripts/t3_rails.py), [`runs/t3/t3_rails.txt`](runs/t3/t3_rails.txt)). Fitted gauge
1.56–1.62 m (rail-head centres; 1.52 m nominal); in the 7 frames within 0.06 m of 1.52 m the cube's centre is
1.133–1.189 m right of the rails' midpoint (median 1.165, IQR 1.147–1.179); the 3 others give 1.05–1.15. The picture
[`runs/t3/png/rails_f278.png`](runs/t3/png/rails_f278.png) shows the two rails as clean parallel lines and the cube's
inner face ~0.1 m outside the right rail head. Inside the rails' own range (frames 276–279, cube 19–23 m) K2-off's axis
matches that midpoint within 0.04 m; at 9.5–15 m (frames 280–284) both axes run 0.05–0.31 m right of it, pulled by the
cube beside the right rail, which is why an axis-based "near-range" offset reads ~0.95 m.

**Frame by frame** ([`scripts/t3_trace.py`](scripts/t3_trace.py): the jury runner with variant B's overrides, hooked
read-only; its records equal the plain run's in every field but the latency health message; run on `972d19a`, whose
`resense/track.py` is unchanged on `main` `8c2bf51`, where M-1 gives the same per-object result; [`runs/t3/`](runs/t3/)):

| frames (near face) | K2-off axis error | B axis error | cube's inner face from: K2-off / B axis (strict limit) | what the detector does |
|---|---|---|---|---|
| 254–258 (63–57 m) | −0.30…−0.43 | −0.24…−0.30 | 0.49–0.61 / 0.62–0.68 (0.95–0.96) | K2-off: a 10–11-voxel `low` cluster from 257, track 93; B: 4 voxels at 257, none at 258 |
| 259–266 (55–41 m) | −0.21…−0.37 | −0.11…−0.22 | 0.55–0.70 / 0.70–0.81 (0.97–0.99) | K2-off: STOP every frame (track 93 confirmed at 259); B: no cluster at 259, 261, 264, otherwise thin/4–8 voxels; track 101 dies at 259, track 104 starts at 262 |
| 267–273 (40–30 m) | −0.08…−0.16 | −0.06…+0.06 | 0.76–0.83 / 0.86–0.98 (0.99–1.00) | K2-off: STOP; B: 2–6 strict voxels, zone `warning` at 268 and 272, track 104 not confirmed |
| 274–279 (28–19 m) | −0.04…−0.08 | +0.02…+0.18 | 0.84–0.88 / 0.94–1.10 (1.01–1.02) | both STOP from 274; B loses 279 (0 strict voxels at 277 and 279) |

(Error = axis − true axis at the cube's near face, + = left, away from the cube.) The cube gives few returns at 30–60 m
(4–13 voxels), and its points are judged by the low-object stage against the bed cross-section learned per lateral
`dy`, so a 0.1–0.2 m shift of the axis decides whether they form a cluster at all. Beyond 60 m B's curvature step
(−2·10⁻³ 1/m at the 60 m knot) follows a left-wall segment that sweeps from +1.2 to −2 m at 68–92 m
([`runs/t3/png/tunnels_f262.png`](runs/t3/png/tunnels_f262.png)); that bend is beyond the cube and does not reach it.

**Set O `small_center` (§6 of revision 1, package row 1) is a different case.** The 0.3 m box hangs 0.95–1.25 m above
the rail head "in the middle of the gauge" (organizers). From the gate rows
([`scripts/t3_small_center.py`](scripts/t3_small_center.py), [`runs/t3/small_center.txt`](runs/t3/small_center.txt)):
at 55.8 m its centre is 0.76 m from K2-off's axis and 0.89 m from K2's (inner edge 0.61 / 0.74 m), well inside the
gauge in both; K2 simply has no detection or warning on it in frames 337–338 and STOPs from 339 (52.5 m), K2 off from
337. So K2 does not lose it at the gauge edge as it does the cube. If the box really hangs on the track's centre line,
both axes are 0.5–0.9 m off on this curve at 30–56 m, K2's by about 0.1 m more; not verified (no rails at that range).

**The ride's removed STOPs at 30–60 m.** On `main` the strict detections K2 removes at 30–60 m are `new_data_4`
1223–1228 (36.9–43.3 m) and `new_data_5` 814–824 (40.1–47.6 m), 1.2–1.4 m from K2-off's axis and 1.4–1.75 m from K2's
([`k2_removed_8c2bf51.json`](runs/t3/k2_removed_8c2bf51.json); `new_data_7` 623–644 of the v5b list are no longer
among them). Replayed with [`scripts/t3_ride.py`](scripts/t3_ride.py) (records equal the gate's: 0 rows differ) and
measured with [`scripts/t3_ride_rails.py`](scripts/t3_ride_rails.py) (rail pairs per 2 m bin): the rails resolve only to
13–19 m in these frames ([`runs/t3/png/ride_nd4_1228.png`](runs/t3/png/ride_nd4_1228.png)), and their midpoint
extrapolated to 37–48 m jumps by up to 1.4 m between consecutive frames ([`runs/t3/ride_rails.txt`](runs/t3/ride_rails.txt)).
**Which axis is right at these detections is not established**, so whether they are the same mechanism as the cube is
open. They are what an OR-of-gauges rule would bring back, and the gate counts each as a false STOP.

**Limits.** One recording, one object. The true axis is extrapolated 0.5–5 m from the rails in front of the cube;
the fitted gauge reads 0.04–0.10 m wide, so the midpoint carries a few centimetres of uncertainty, much less than the
0.1–0.2 m differences above. The synthetic bag's own track geometry is not known otherwise.

## 8. Not done (updated 20.10 after the data run)

- G-2 (X3) for v5c-30: not run (v5c-30 already fails M-1 on a second object).
- Set O `small_center` 55.8 → 52.5 m (§7): inside both gauges; why K2 has no detection in frames 337–338 is not traced.
- The ride's strict detections removed at 30–60 m (§7): which axis is right there is not established (rails resolve
  only to 13–19 m).
- The platform cube under v5c-30 (§6): the `doubt` hold is inferred from the records, not traced.
- The 9 near STOP frames on Falcon at 5–6 m (4373–4379, 4410–4411, every K2 variant) are still not attributed.
- Review by P3 or a fresh agent; the captain's decision.
