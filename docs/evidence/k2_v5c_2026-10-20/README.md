# K2 v5c: keep genuine detections beyond the reach cap (20.10)

> **Owner:** P4 (author; the review is by P3 or a fresh agent) · **Decides:** the captain · **Status:** code and
> offline evidence. The variant is **not measured on the data**: this container cannot reach Google Drive or Yandex
> Disk (network policy), so no bag or cache was available. Every switch stays **off** by default; nothing ships until
> the measurement below runs and the captain decides. G3 not touched.
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
2.6 m later. In the 36 frames the person is a
warning, `beyond_axis` (19), `beyond_height_ref` (2) or no reason (15, tracker votes after the demotions), because the
reach cap ends the trusted range at the walls' reach + 15 m.

## 2. v5c: what both axes put in the gauge stays an obstacle

**Switch:** `track.axis_joint_reach_dual` (m, default **0.0 = off = v5b**), in `resense/config.py` and both YAMLs.

With the reach cap on, the cap is where the walls stop confirming the joint shape. v5b ends the trusted range there,
so everything beyond becomes advisory, true objects included. v5c moves that end out by `axis_joint_reach_dual`
metres (never past the base estimator's own range) and, between the cap (`track.joint_reach`) and that end, counts a
point as strict gauge only when it is inside the gauge measured from the joint axis **and** from the base axis
(`Detector._corridor`; the rails' fallback membership `in_rail` too). Everything else is v5b.

Why this targets the genuine detections and not the false ones: the base axis is trusted that far without K2, so an
object inside both gauges is one that neither shape can explain away. The two false alarms v5b's cap was traced to
remove ([`V5.md`](../k1_k2_gauge_2026-10-19/V5.md) §6) lie inside only one: roundT_doubleT frames 96–99 (base axis
5.2 m off the driven path, the cluster 1.6 m from it) and set O background 661–665 (base and joint axes 1.3 m apart at
118 m, on opposite sides).

Code: `resense/track.py` `_joint_output` (the extended range), `resense/detector.py` `_corridor` (the dual
membership). Tests (`tests/test_k1_k2_axis.py`, 2 new): 0 is v5b bit for bit and the range never passes base's; beyond
the cap an object between the two axes stays strict, one inside the joint gauge only does not, before the cap nothing
changes, off nothing changes. Mutation checks: removing the membership line fails the scene test; dropping the
extension fails the range test. `tests/test_k1_k2_axis.py` 23 passed; late candidates, modules, algorithm, wall drift,
edge axis, node, native: 234 passed, 42 skipped.

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
STOP frames. On Falcon the 36 lost frames at 113–125 m are inside both gauges (base lateral −0.56 to −1.0 m with a 0.8 m wide
cluster, joint lateral 0.07–0.4 m) and at most 13.7 m beyond the monitored range, so v5c at 15 m is expected to restore
them (inferred: the monitored range is not exactly the trusted range). With 30 m the proxy adds one frame on
`new_data_5` and one on `new_data_6`.

## 4. Registered before measuring (rows, values, criteria)

Candidate **v5c-15** = variant B + `axis_joint_reach_dual: 15.0`; fallback **v5c-30** (30.0) only if F-1 fails at 15.
No other value is tried. Reference: the committed defaults of the measured commit (K2 off), as in the integration
evidence.

| # | row | criterion |
|---|---|---|
| F-1 | Falcon, whole recording, [`score_falcon_pos.py`](scripts/score_falcon_pos.py) | person first STOP ≥ 124.0 m; decision-level lost person frames ≤ 5; no new STOP frame beyond variant B's 9 |
| G-1 | full gate, seal baseline, no `--allow` | the only failing rows are set O `small_center` (variant B's accepted exception); ride STOP episodes ≤ 12; five empty recordings and squareT_platform 0 episodes |
| G-2 | X3 battery vs the committed reference | not worse than variant B |
| K1-2 | standing person at 150 m (`S_person_150`) | reported (v5b 0 / 260, base 90 / 259) |
| ID | every switch off vs the commit without this change | identical per frame (gate and Falcon) |

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
- The 9 new near STOP frames on Falcon (4373–4379, 4410–4411) are not attributed.
- Review by P3 or a fresh agent.
