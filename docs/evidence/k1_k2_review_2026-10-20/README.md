# K1/K2: independent v5c review — NO-GO for switch-on

> **Purpose:** review the measured candidate and hand the remaining work to its owners.
> **Audience:** P3 / P4 / captain · **Reviewer:** new OpenCode session, not an author of v5c
> **Date:** 2026-10-20 · **Current source reviewed:** `f56ad5e6` (main at intake)
> **Historical data source:** `8c2bf51` · **Status:** review delivered; detector repair / final acceptance blocked on the role handoff below.

**Subsequent role update (20.10):** the user reassigned this session to P3 for
implementation. [Author repair record](../k1_k2_repair_2026-10-20/README.md).
The ownership pause in §3 is historical; a different reviewer must accept the
new patch. The v5c findings and NO-GO recommendation below remain unchanged.

**Recommendation: keep both K1 and K2 off.** The measured v5c candidate does not pass the original acceptance
contract. Reducing false alarms does not resolve its positive-object losses. The captain's decision 44 remains
the effective switch decision; this report supplies a reviewer recommendation, not a new captain decision.

## 1. What was done

- Updated local main to `f56ad5e6`, then created `review/k1-k2-v5c-20261020` as the handoff requires. Read the
  repository overview/architecture, current role plan, freeze procedure, original K1/K2 protocol and reviews,
  v5 package, v5c data report and post-measurement proposal. Reviewed the K1/K2 implementation and its tests,
  range-cap/dual-zone call sites, and both Falcon scorers.
- Committed [review scope](PROTOCOL.md) before executing the review checks.
- Re-scored 27 hashed committed inputs: all three 4,443-row Falcon runs, all three marked bags for each of off/15/30
  (**1,667 rows per configuration**), four standing-person reports, gate and X3 reports.
  [Reproducer](audit.py), [machine-readable audit](audit.json).
- Recomputed all 260 X3 comparisons per variant from the recorded 40-case metrics. They exactly match the stored
  comparisons. This is a report re-score; the full 29,765-row X3 raw replay was not repeated here.
- Checked native and numpy paths for a newly identified missing-floor defect on current code, using a deterministic
  synthetic cloud and an unchanged-input control. [Reproducer](probe_missing_floor.py), [result](missing-floor.json).
- Ran the existing K1/K2, wall-drift, rail-extension, gauge stability/display and native tests: **88 passed, 2 skipped**.
  The two native end-to-end tests require unavailable `open3d`; no failed test was suppressed.
  [Environment, commands, source hashes and checks](checks.json).
- `detector_freeze.py verify`: **PASS**, 40 files, digest
  `6d091081769104657ecc2c0b06f53049647d4f6c7327b7429bbda92673782452`.
  Both YAMLs are synchronized and K1/K2 defaults are off. The detector/configuration source is unchanged.

No new recording replay was performed. `/data` is absent on this host; the committed outputs are sufficient for
this review, not for testing a repaired candidate. Main's later F1a/L16/R3 changes affect eight production/config
files relative to `8c2bf51`; historical numbers cannot be transferred to the current source as acceptance.

## 2. Findings that block enablement

### R1. Falcon aggregate gains still conceal ten lost original person STOP rows

The unchanged proposed `score_falcon_person.py` reproduces its published totals. Inspecting its **matched-frame sets**,
and independently checking the candidate decision in each lost frame, gives:

| run | first person STOP | person STOP rows | original rows lost | new person rows |
|---|---|---:|---:|---:|
| off | frame 2972, 124.84 m | 1360 | 0 | 0 |
| v5c-15 | frame 2979, 124.02 m | 1366 | **10** | 16 |
| v5c-30 | frame 2950, 127.18 m | 1374 | **10** | 24 |

Lost in **both** candidates: `2972–2975`, `3059–3063`, `4382`. Every one has no candidate STOP, independently of
the matching tolerance. v5c-15 is seven frames / 0.82 m later at first detection. Thus the post-hoc criterion
“person STOP total ≥ reference” does not establish retention. The original protocol F-1 requires every original
person STOP to remain. Do not replace it retroactively with an aggregate count.

The position scorer is useful for attribution, but its positions come from reference detections/warnings and
extrapolation, not independent annotations. It indexes records by list position without checking IDs/timestamps;
the review validates all 4,443 IDs and timestamps before using it. Future acceptance tooling must fail closed on
misaligned/incomplete inputs and report matched lost/gained frame sets. Frames 4410–4411 remain unattributed.

### R2. The full strict gate and X3 fail

Both candidate gate reports explicitly have `gate.passed=false`, no waivers, and six failed `small_center` metrics.
The v5c table's G-1 “pass” is its narrower row allowing the historical exception, **not a passing strict gate**.

- `small_center`: 32 →30 STOP rows; first 55.8 →52.5 m; held 60.8 →57.5 m. Missing-streak/span and 50–100 m rows also fail.
- v5c-15's 260 X3 comparisons include **six failures**: crossing-person loss under +2° roll (four rows), dropout seed 2
  and dedup (three rows each); positive-recording roll loss (four); Set O at 5 Hz loses four positive-recording rows
  and four `small_center` rows. Record-level and object-level comparisons overlap; these are not six distinct objects.
- Gains remain real on the historical source: ride STOP episodes 24 →10, five empty recordings 11 →0.

Recalculation uses the maintained comparison functions and exactly reproduces the stored verdicts.
Self-comparison passes; a planted additional three-frame positive loss is rejected. No tolerance was changed.

### R3. Marked-object losses remain in-gauge misses

An independent implementation of the registered marker-box matching reproduces the per-object results for all
three bags and configurations:

| marked object | off | v5c-15 | v5c-30 |
|---|---|---|---|
| tunnels 19 | 29 STOP rows; 54.994 m first | **13; 27.607 m** | **13; 27.607 m** |
| platform 23 | 38; 86.755 m | 40; 89.492 m | **31; 76.439 m** |

Tunnels 19 loses `259–273,279`; platform 23 with the 30 m extension loses `106–112`. Every other marked object has no lost reference
STOP row in this re-score. Self-comparisons and a planted lost detection on each bag validate the comparison.
The review's first audit attempt rejected incorrectly assumed bag lengths; counts were corrected from the actual
marker inventories to platform 386, switch 736, tunnels 545. Every frame ID is now checked, not truncated to a prefix.

The retained rail plot (`../k2_v5c_2026-10-20/runs/t3/png/rails_f278.png`) shows the cube intersecting the envelope
beside the right rail; the roll frame 10 plot shows the entering person's edge sensitivity. Both were inspected.
The T3 rail reconstruction places the cube's inner face 0.05–0.08 m inside the strict envelope. An explanation
that the reference axis is more displaced does not make an in-gauge missed object acceptable under the organizers'
rule. The proposal to mark M-1 “explained, not a regression” is **not accepted by this reviewer**. The absolute rail
reference and ride 30–60 m removals still need raw-cloud validation; this review does not independently refit them.

### R4. Standing person at 150 m is unresolved; K1 is not accepted

Summing the saved visible/hit rows reproduces off **90/259**, B/15/30 **0/259**. The original K1 threshold is
≥150/259. The existing package also reports 65 of the reference's 90 hits matching a static structure; this review
does not independently validate that attribution. Even the unrevised reference total fails the target.
The v5c run has **K1 off** and cannot be presented as K1 acceptance. A corrected target-specific probe must preserve
the historical result, distinguish the target from background, and run 100/150 m, sudden appearance and false-STOP controls.

### R5. New current-code defect: missing bed fit releases the K2 cap

`resense/track.py:1222–1250` replaces the prior with `prev.base` before fitting. If `_fit_floor` returns `None`, it
calls `_joint_output(prior, jprev, cfg)` without boundaries. `_joint_output` resets `joint_reach=0` and copies the
uncapped base range (`:1467–1485`). `Detector._dual_zone` then returns immediately (`resense/detector.py:842–844`).

Reproduced with the existing transition-curve fixture: eight settling frames followed by **63,548 retained points**
outside the base bed-fitting band. This is not an empty-input shortcut. Results are identical with numpy/native:

| setting | previous `axis_valid` | next, without a bed fit | `joint_reach` |
|---|---:|---:|---|
| B, extension 0 | 147 m | **163 m** | 147 →0 m |
| v5c-15 | 162 m | **163 m** | 147 →0 m |

The ordinary off estimator holds its prior exactly (control). At 148 m a constructed cluster inside the joint strict
gauge but outside the base gauge changes from `warning/beyond_axis` to `gauge` in the v5c dual classifier solely
because the cap marker vanished. **This is estimator/classifier evidence, not an end-to-end false STOP or measured
recording exposure.** P3 must preserve or conservatively decay the output's capped state across missing observations,
without feeding the joint shape back into the base estimator. Add a failing regression first and verify recovery
when observations return. An implementation must not blindly retain stale trust indefinitely.

## 3. Role conflict and ordered handoff

The old P4 package says “P4 develop and measure”; the latest
[`PROPOSAL_r3.md`](../k2_v5c_2026-10-20/PROPOSAL_r3.md) explicitly assigns detector changes to **P3**.
`CLAUDE.md` and BACKLOG §1 prohibit a P4 evaluation run from editing detector code. This fresh reviewer has completed
the existing-candidate review. Authoring the next production repair here would both cross that boundary and remove
the independence of this session's subsequent acceptance. **Implementation is paused at that boundary, not declared complete.**

| order | owner | needed next / completion condition |
|---|---|---|
| 1 | P1 + P3 | Confirm the detector-repair owner and isolated branch from the latest seal. If this session is reassigned to P3, name a different independent reviewer. |
| 2 | P3 | Commit defect tests before measurements; address R5, the missing `small_center` candidates, crossing-edge confirmation losses, marked-object low-stage sensitivity and standing-axis trust/convergence. Trace actual fired rules; prove traced/plain equality. No global OR-of-gauges or wider dual interval without controls. |
| 3 | P4 + author | Register revision 3 **before** candidate measurements, retaining original failures; specify target/axis reference and scorer alignment. Obtain gate/decoded caches and raw Falcon/marked bags from the existing data handoff. |
| 4 | P4 | Paired off/candidate runs on the exact repaired source: strict gate without exceptions, X3, whole Falcon with frame-level retention, all marked objects, K1 targets and K2/B6 curve accuracy/range honesty. Off-identity and positive controls required. |
| 5 | independent reviewer | Review the repair and raw changed frames, including all lost/delayed/shortened positives and new false alarms. |
| 6 | captain / P1 | Decide switch-on only after the evidence/review; final default-config gate, integration checks and reseal. Until then decision 44 stays in force. |

G3 remains untouched. No switch was enabled, no detector repair or new seal was published, and no application
deployment was performed by this documentation/evidence review. The working deliverable is the committed review
branch; merge and the next role assignment belong to the captain.
