# F1a completion — the rail head's own top surface as the reference (20.10)

> **For:** the captain and P4 · **From:** P3, on the user's request to complete F1a · **Detector code:** changed
> (`resense/lowobj.py` only) · **Candidate:** `fix/f1a-completion` `a77d884` (the production change) · **Reference:**
> `main` `f56ad5e` (the tree of the B1 repair's independent acceptance) · **Environment:** `OPENBLAS_CORETYPE=Haswell
> OMP_NUM_THREADS=1`, Python 3.12, numpy 1.26.4, as in
> [`../f1a_acceptance_2026-10-20/README.md`](../f1a_acceptance_2026-10-20/README.md).

## Answer

1. **The B1 repair's ride cost is gone.** The chunked ride gate against current main: alarm events **23 → 18**,
   STOP episodes **26 → 24**, alarm frames **111 → 102** — exactly the pre-repair values recorded for `8c2bf51`
   (18 / 24 / 102). Every one of the 9 STOP frames the B1 repair had added is removed, and **no new STOP frame
   appears anywhere**. The other five recordings and every set O object are unchanged; `doubleT_platform` loses the
   2 advisory frames the repair had added. The strict gate passes with **no waiver**.
2. **No detection is lost.** The organizers' set O objects are identical row for row, including the low-lane
   controls that matter here: `long_low_on_rails` (52 STOP frames, first 87.2 m), `small_on_rail` (23 frames, 42.7 m)
   and `thin_hanging` (18 frames, 35.1 m). `doubleT_obstacle`'s labelled hits are unchanged. The whole Falcon stream
   (4,443 rows) is field-identical, and the standard X3 battery passes **0 of 260 comparisons failed** over 40 cases.
3. **Why it works.** The frame's rail returns are **bimodal**: the lower mode is the rail *web*, the upper mode the
   head's *top surface*, and on the ride both rails read both modes synchronously. The model's rail-head plane sits
   about 0.1 m below the real head top there. The F1a reference was the **median** of the band, so it read the web,
   while the B1 repair's uncapped top read the head's top: the comparison was between two different features, and the
   head's own top was reported as an object's body. The completion reads the **same feature** on both sides of the
   comparison — the head's top surface.
4. **The new rule cannot add a rejection the pre-repair F1a did not make.** It only applies to a cluster the
   pre-repair rule rejected (capped top below the original median reference). Its rejection set is therefore a subset
   of the pre-repair rule's, and on the recordings that set contained no real object (T4's independent visual
   exposure, [`../f1a_exposure_2026-10-20/README.md`](../f1a_exposure_2026-10-20/README.md)).

## The change

`resense/lowobj.py`, one new helper and one new branch in `rail_reference_check`:

* `_rail_surface_reference` reads the **head's top surface** in the candidate's own lateral band: the highest
  low-free return in that band, on the same height window the top uses (`foot_max_top`). Conditions, all
  parameter-free: the candidate is narrow and its lateral interval reaches an expected rail line
  (`rail_start_max_width`, `rail_start_lateral` — the geometry `mark_rail_line` already uses); both along-track
  sides carry at least one low-free band return; the surface is seen by at least **two distinct** returns within
  `rail_start_margin` of it (the cloud holds every return twice, so duplicates must not count as support).
* The branch fires only for a cluster the **pre-repair** rule rejected, and only when the uncapped footprint top
  does not rise above that surface by more than `rail_start_margin` (the existing 0.05 m, half the organizers'
  0.10 m object).
* The pre-repair rule, the B1 repairs' independent low-free reference, the margins, the weak/advisory modes and the
  configuration are unchanged. The unsafe ablation `local_rail_exclude_low=false` keeps the new path **off**: with no
  low-free mask there is no independent support, so the ablation cannot become a second self-support mechanism.

The protocol, the two intermediate candidates and the amendments are in [PROTOCOL.md](PROTOCOL.md); the raw-state
diagnostics that produced the head/web reading are in [`out/`](out).

## How it was checked

| check | method | result |
|---|---|---|
| strict gate | `regression_gate.py` on the clean `a77d884` tree, seal baseline, `--jobs 2`, no `--allow`; both sides run | **PASS**, no waiver, no missing or worse gated row ([`out/gate_rows.txt`](out/gate_rows.txt)) |
| ride against main | the two gates' per-frame JSONL, row by row | 19 changed frames: **9 STOP frames removed, 0 added**; 10 advisory-only changes; the removed frames are exactly the ones P4 traced to the repair (ride 1 tracks 288/305, ride 4 track 50, ride 7 track 202) ([`out/changed_frames.txt`](out/changed_frames.txt)) |
| ride against the pre-repair rule | the recorded `8c2bf51` numbers of P4's acceptance | **18 / 24 / 102** — the pre-repair values, exactly |
| no detection lost | set O per object and `doubleT_obstacle`'s labelled hits, candidate against reference | identical for **every** object; `long_low_on_rails` 52 frames / 87.2 m, `small_on_rail` 23 / 42.7 m unchanged |
| the other recordings | per-recording rows of the two gates | identical, except `doubleT_platform`'s advisory frames 182 → 180 (the repair's 2 advisory frames) |
| physical scenes | the P4 raised-rail scenes (3 rail elevations × 4 box tops × empty controls, plus a 45-frame approach) on both trees | 32 scenes, **0 differing rows**: the 5 positive cases keep 8 matched STOP rows each, all 6 empty controls stay empty, the approach keeps its 38 matched rows from 54 m ([`out/physical_compare.txt`](out/physical_compare.txt)) |
| B1 controls | `tests/test_f1a_b1.py` and `tests/test_f1_false_alarms.py` | 12 two-rail fragments confirm as ordinary gauge tracks; the fragmented object, the missing-support, the cant and the both-rails-raised cases hold ([`out/targeted.xml`](out/targeted.xml)) |
| the new rule | `tests/test_f1a_continuation.py` | the head's top surface rejects an uncapped fragment on both rails and under a slope; a body above it does not; a single stray return, a neighbouring object's returns, a wide cross-track surface and an originally accepted top do not reject |
| which flips are explained | P4's archived raw snapshots of all 98 flipped clusters, the production function applied to them | **85 of 98** explained by an independently observed head surface; the 13 remaining are listed with their cause ([`out/flips.json`](out/flips.json)) |
| whole Falcon | the 13.10 judge probe over the whole stream, both trees | 4,443 rows, **0 differing fields**, identical decisions (1,364 STOP / 3,070 CAUTION / 8 GO / 1 FAULT) |
| X3 | the standing battery with the unchanged judge probe, fresh on both trees, candidate against reference | **0 of 260 comparisons failed**, 40 cases; one raw field differs: the `clear` distance in one `roll_p2` row (4.8 → 26.6 m), which **restores** the pre-repair value — the near low cluster that capped it is weak again; the detection and the decision are identical |
| tests | affected suites, then the full suite | 363 affected tests pass (1 external-data deselection); the full suite's result is in [out/full-tests.xml](out/full-tests.xml) |

**Positive controls.** The audit's own comparison is not vacuous: damaging a metric makes it fail, and the same
tools are run on a case with a known answer (the raised-rail box, 8 STOP rows; the empty controls, 0). The 13
unexplained flips are reported, not hidden.

**Instrumentation.** The archived snapshots are P4's own raw dumps; the production function is imported from the
candidate tree, so the attribution is the production branch's, not a re-implementation's. The traced runs (the
archived P4 trace) and the plain gate rows were already shown equal outside timing by P4.

## Not checked / limits

* The ride has no ground truth: the frames removed are rail fragments by P4's picture review, not by a label.
* The head's top surface is read from the frame's own returns, so a rail head whose top is never crossed by a ring
  in the window is not explained: this is the 13 remaining flips. The rule then fails **open** (the cluster keeps
  ordinary confirmation).
* The margin is the existing `rail_start_margin` (0.05 m). An object lower than 5 cm above the head's top surface is
  not distinguished from the head; the organizers' object is 10 cm.
* The new path needs the low-free mask; with `local_rail_exclude_low=false` (the unsafe ablation) it is off.
* This is **author evidence on committed source**, not independent P4 review, not a release and not a new seal on its
  own: the integrity seal is source integrity only.

## Files and reproduce

`out/`: the gate reports of both sides, the per-frame comparison, the physical comparison, the flip analysis, the
targeted and full test XML. `PROTOCOL.md`: the registered acceptance and its amendments.

```
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
python docs/evidence/f1a_completion_2026-10-20/run_checks.py gate --side candidate --revision c
python docs/evidence/f1a_completion_2026-10-20/audit.py --out docs/evidence/f1a_completion_2026-10-20/audit.json
```
