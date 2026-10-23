# F1a bounded head top — 21 October 2026

> **For:** the captain and the independent reviewer · **From:** P3 (author evidence, not acceptance) · **Branch:**
> `claude/f1a-bounded-1.3` · **Control:** v1.2.0 `3b73bbe`, fresh runs in a detached worktree · **Protocol:**
> [PROTOCOL.md](PROTOCOL.md) (pre-registered `2fa1ec4`; amendment 1; revision 2 `d9d8105`; amendment 2) ·
> **Held-out G3:** not touched. `scripts/detector_freeze.py verify` fails on this branch by design (detector source
> edited; the captain reseals).

## Answer

**The switch `lowobj.rail_head_bounded` is OFF in the final commit (`1fc6fd7`; class default and both YAMLs,
`sync_params.sh --check` passes).** Made safe against the independent review's attacks, the rule keeps almost none of
the ride gain and adds an indirect STOP episode on the ride, so the pre-registered ride row C1 fails.

| revision | measured | synthetic (no real detection lost?) | ride, chunked gate (events / episodes / STOP rows) | ride, continuous (STOP rows) | verdict |
|---|---|---|---|---|---|
| 1 + amendment 1 | `61b6e1a` | my rows pass; **the review found losses** with real per-ring phases, ramps, a pipe across the rail, cant (`apb_meas` 709 → 700, `shapes` 1,075 → 1,067, `cant` 336 → 332, `seeds` 21 lost) | 23 → 21 / 26 → 26 / −2, +0 | 120 → 116, 0 added | **REJECTED** by the independent review |
| 2 + amendment 2 | `35ff9f4` | **every row passes**: 13 review families as defined, 10 families × 3 seeds with real phases forced, my 12 earlier families: **0 frames lost, 0 later** | 23 → 22 / **26 → 27** / −2, **+2 (rows 1269–1270)** | 120 → 119, 0 added | **C1 fails → switch off** |
| final | `1fc6fd7` | switch off | per-frame identical to v1.2.0 (see "Final state") | — | shipped off |

The user's goal (F1a's trade-off acceptable *and* on) is **not reached**. What this lane leaves: a rule that is safe
on every synthetic attack measured so far (revision 2), the evidence that its safe form does not buy the ride
improvement, and the reasons (below), so the next attempt does not repeat the dead ends.

## Revision 2 — the rule as it stands in the code (off)

`resense/lowobj.py`: `rail_head_top`, `_faces_sensor`, branch in `rail_reference_check`. A clean low gauge cluster
that the B1 rule keeps becomes weak again only if all hold: the low-free mask is in use; the **pre-repair** rule
rejected it; it is ≤ 0.45 m wide and reaches exactly one rail line; **H** = per rail the lower of two low-free maxima
(own rail before / after its extent ± 0.3 m, other rail before / after its centre, within 5 m), the two rails'
levels **agreeing within 0.03 m** (cant → fail-open), H ≤ 0.25 m above the plane; **no return of the object's full
extent** (its lateral extent ± 0.05 m, x0 − 0.3 … x1 + 1.0 m, below 1.5 m) more than 0.03 m above H; the top surface
over that extent ≤ 0.10 m wide; and **no face toward the sensor** (two footprint returns within 0.05 m along and
0.07 m across, 0.03–0.30 m apart in height: one ring is a cone of near-constant elevation, so returns at one range
and different heights come from different rings). Every missing piece of evidence keeps the cluster.

Root causes the review named and how revision 2 answers them: F6 (the compared top was the maximum inside the
cluster's own box) → the full-extent search and the extent-wide top surface (amendment 2: a ramp crossed by one
ring at head height had 4 of its 5 returns 1–2 mm outside the box); F1 (real per-ring azimuth phases defeat a 2 cm
face test) → 7 cm, justified by the ring-cone geometry; F3 (cant) → the rails must agree.

## Results of revision 2 (`35ff9f4`, switch on) against v1.2.0

| # | check | control → candidate | pass |
|---|---|---|---|
| R1 | 13 review families as the review defined them (`attack.py`, `rc2.py` unchanged): `apb` 831, `apb_meas` 709, `ext_meas` 287, `azoff` 827, `fine_delta` 444, `shapes` 1,075, `two` 273, `cant` 336, `curve` 515, `moving` 272, `falcon` 252, `empty` 0, `seeds` 409 | all equal: 0 lost, 0 gained, 0 later; gauge detections equal | ✅ |
| R1 | my fresh control rows vs the review's archived control rows | equal in all 13 families | (instrument) |
| R1 | positive control: revision 1 `61b6e1a` on `apb_meas` / `shapes` / `cant` | 709 → 700, 1,075 → 1,067, 336 → 332 = the review's numbers | (instrument) |
| R2 | `apb`, `fine_delta`, `shapes`, `two`, `cant`, `curve`, `moving`, `empty`, `ext_meas`, `azoff` with measured phases forced, seeds 0 / 101 / 202 (30 runs per side) | all equal: 0 lost, 0 gained, 0 later on every seed | ✅ |
| R3 | my earlier 12 families (review `synth_controls.py` 8 + `ext_scenes.py` 4) | all equal (831, 283, 113, 72, 48, 965, 883, 342, 71; empties 0) | ✅ |
| A4 | `tests/test_f1a_bounded.py` | 67 / 67 | ✅ |
| B/D3 | full gate (no `--allow`) | exit 0, `GATE PASS` against the registered baseline; set O, `doubleT_obstacle`, five empty recordings: no STOP row lost or added (per-frame) | ✅ |
| C1 | ride, chunked gate vs v1.2.0 | events 23 → 22, **episodes 26 → 27**, STOP rows: piece 1 row 1265 and piece 4 row 80 removed, **piece 1 rows 1269–1270 added** | ❌ |
| C2 | ride, continuous replay | STOP rows 120 → 119 (row 2677 removed), episodes 26 → 26, low-kind 3 → 3, 0 added | (reported) |
| D1 / D2 | Falcon, X3 | **not re-run for revision 2** (the switch stays off, so they cannot change the decision; their data caches had to be deleted for the ride; revision 1 passed both: 4,443 rows identical, 0 / 260) | — |

**Why rows 1269–1270 appear** (`trace_piece.py`, traced == plain on all 1,409 rows of the piece): track 310, a low
cluster at the track **centre** (lateral 0.01 m, ≈ 30 m), confirms in the candidate and not in v1.2.0. The new branch
never touches that cluster (it is not rail-eligible); it rejected rail fragments in rows 1259–1267 (11 rejections),
which changed which tracks the following low clusters joined. Revision 1 rejected a different subset there and did
not produce it. The ride has no objects, so these are false STOPs, caused indirectly.

**Why the gain disappears:** the ride's rail fragments are what a 5 cm object's front face looks like at 30–40 m
(2–4 returns at head height). What separated them in revision 1 was evidence an object can also lack (no top-face
hit inside a 0.3 m box, no stacked return within 2 cm), and the review showed real objects that lack it. Revision 2
asks for evidence a real object reliably supplies; the fragments that remain rejectable after that are few (the
gate's two removals survive, the continuous replay keeps one of four), and the changed track history around them
can add as well as remove a STOP.

## What was checked, and how

* Every comparator has a self-test and a positive control (`compare_synth.py`, `compare_rows.py`, `compare_gate.py`,
  `compare_physical.py`; `compare_gate.py` reproduces the review's numbers on the rejected completion's archive).
* Synthetic instruments: the review's own harness unchanged (`REVIEW_SCRIPTS.sha256`: branch
  `claude/f1a-bounded-review-1.3` @ `15c3d0f`); my fresh control rows equal the review's archived control rows in all
  13 families; revision 1 reproduces the review's losses. `attack_r2.py` only forces `az_off = measured` and the seed.
* Ride attribution: traced == plain on every traced piece; the first changed row of each changed piece is a row where
  the new branch rejected a cluster (revision 1: 1259 / 1327 / 74 / platform 31; revision 2: piece 1 from 1259).
* Raw data: 37 pictures of revision 1's ride / platform rejections (`raw/61b6e1a/trace.tar.xz`, examples in
  [pictures/](pictures/)); revision 2's design on those 37 raw-point dumps (`design_r2/`).
* Final state (switch off, `1fc6fd7`): the full gate's per-frame rows against v1.2.0 — see below.
* Timing (revision 1, serial, 1,409 ride frames): p50 28.3 / 27.6 ms (control) vs 26.7 / 27.3 ms, p95 48.3 / 48.7 vs
  46.5 / 47.9 ms; no measurable cost. Revision 2 adds a bounded search per eligible cluster (a few per frame at most);
  gate timing for it is in `raw/35ff9f4/gate_ride.tar.xz`.

## Final state

`1fc6fd7` (switch off), full gate against the registered baseline: **exit 0, `GATE PASS`**, no `--allow`. Against
the fresh v1.2.0 control: **all 15 per-frame files identical** (15,269 per-frame rows, 0 changed); the only differing result leaves are the ride's health ok / warn counts
(11,009 / 262 → 11,088 / 183), which follow the wall-clock latency budget. Affected tests on `1fc6fd7`: 412 passed,
1 failed = the pre-existing ride-cache test above (identical on v1.2.0). The shipped detector therefore behaves as
v1.2.0; the new code is inert unless `lowobj.rail_head_bounded` is set.

## Failures and corrections along the way

* Revision 1 `086353d` failed my own A1 (13 frames, 5 cm boxes); amendment 1 fixed it on the ideal-grid caster only.
* Revision 1 `61b6e1a` passed all my pre-registered rows and was **rejected by the independent review** (F1–F6).
* Revision 2 `f1f6f44` failed one `shapes` scene (ramp at head height, 1 frame); amendment 2 fixed it; all rows were
  re-measured on `35ff9f4`.
* Revision 2 `35ff9f4` fails the ride row C1 (+2 STOP rows, +1 episode).
* Pre-existing, not caused by this lane: `tests/test_rail_start.py::test_finding_rail_heads_ahead_of_a_standing_fresh_start_do_not_stop`
  fails identically on v1.2.0 when the ride cache is present (4 low STOPs at 2.9–3.1 m; normally deselected).
* Environment: the gate requires the ride intake manifest, which the VM_GUIDE §2.3 recipe does not write;
  `scripts/cache_extended_ride.py` does (archive SHA-256 verified).
* My own errors: wait loops that matched their own `pgrep -f` pattern (replaced by PID waits), a selftest crash on
  target-less families, the compact replay without timing, a broken queue script (sed delimiter), a lint failure from
  copying the review's scripts (referenced by hash instead).

## Unverified / limits

* Revision 2 was not run on Falcon or X3 (the decision does not depend on them; it would be needed before any switch-on).
* Synthetic geometry is first-return, no dual returns, beam divergence or motion distortion; the real phase table is
  from one recording's 67 far-reaching rings (the review's).
* The ride is both design and acceptance set; the indirect STOP at 1269–1270 shows that track-history effects of the
  rule are not predictable from per-cluster analysis.

## For a next attempt (not done here)

The per-frame cluster rule cannot tell a rail fragment from a small object's front face at 30–40 m without evidence
the object may not supply. Candidates that use evidence the object cannot fake: persistence over frames (a rail
fragment's "top" stays at the head level as the train moves, an object's front face rises toward its real top as
rings sweep it), or the cluster's position against the frame's own fitted rail line over many frames. Any such
change must also be judged on track-history effects (the 1269–1270 mechanism), not only on per-cluster decisions.

## Reproduce

```bash
D=docs/evidence/f1a_bounded_2026-10-21; REV=<review checkout>/docs/evidence/f1a_bounded_review_2026-10-21
RESENSE_REPO=<wt> python $REV/attack.py --family <F> --out <o>.json --jobs 4                  # R1
RESENSE_REPO=<wt> REVIEW_DIR=$REV python $D/attack_r2.py --family <F> --seed <S> --out <o>.json # R2
$D/run_synth.sh control|cand <out> <families>                                                   # R3
python3 $D/compare_synth.py <control.json> <cand.json> --selftest
$D/run_check.sh control|cand gate|ride|falcon|x3|physical|affected|full <out>
python3 $D/compare_gate.py <ctrl.json> <cand.json> <ctrl work> <cand work> --selftest
RESENSE_REPO=<cand> python $D/trace_piece.py /data/cache <cand work> new_data 1 8 <prefix>
```

Raw outputs: `raw/61b6e1a/` (revision 1, the full A–D set), `raw/pre_amendment_086353d/`, `raw/pre_amendment2_f1f6f44/`,
`raw/35ff9f4/` (revision 2: synthetic R1/R3, gate, ride, traces), `raw/35ff9f4/synthetic_R2.tar.xz`, `raw/1fc6fd7/`
(final switch-off gate).
