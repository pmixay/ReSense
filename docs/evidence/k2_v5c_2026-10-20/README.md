# K2 v5c: keep genuine detections beyond the reach cap (20.10)

> **Owner:** P4 (author; the review is by P3 or a fresh agent) · **Decides:** the captain · **Status:** code and
> offline evidence. The variant is **not measured on the data**: this container cannot reach Google Drive or Yandex
> Disk (network policy), so no bag or cache was available. Every switch stays **off** by default; nothing ships until
> the measurement below runs and the captain decides. G3 not touched. v5c addresses the Falcon person's loss beyond
> the reach cap; the tunnels cube lost inside the cap (§1b) is open, so **K2 is not ready to switch on**.
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

## 6. Not done

- No measurement on data (G-1, G-2, F-1, K1-2, ID): the data is not reachable from this container.
- Set O `small_center` 3.3 m later (package row 1) is the joint shape at 55 m, before any cap; v5c does not touch it.
- The tunnels cube (§1b): inside the cap, not addressed; diagnosing it needs the cloud of frames 255–275.
- The 9 new near STOP frames on Falcon (4373–4379, 4410–4411) are not attributed.
- Review by P3 or a fresh agent.
