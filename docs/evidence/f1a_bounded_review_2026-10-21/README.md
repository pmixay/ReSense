# Independent review of the F1a bounded head top (`61b6e1a`) — 21 October 2026

> **Reviewer:** independent agent (not the author), dispatched by the captain's session. **Candidate:** `61b6e1a`
> (switch `lowobj.rail_head_bounded` on), branch `claude/f1a-bounded-1.3`. **Control:** v1.2.0 = `3b73bbe`. Detached
> worktrees of both (plus the rejected completion `a77d884` as a positive control), native kernel built in each by
> `scripts/build_native.sh`; Python 3.12.3, numpy 1.26.4, scipy 1.11.4, scikit-learn 1.4.2;
> `RESENSE_REPO` = the worktree measured, `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`; `resense.__file__` asserted
> inside the worktree in every run. **No file under `resense/`, `native/`, `configs/`, `ros2_ws/` touched. Held-out
> G3 not touched. Nothing tuned.**

## 1. Verdict: **REJECT**

**The claim "no real or synthetic detection is lost" does not hold. The new branch makes real obstacles weak —
including objects 10 cm above the rail head (the organizers' minimum height) — and costs STOP frames and first-STOP
range against v1.2.0, in scenes the author did not test: with the real sensor's per-ring azimuth phases, a ramp
sloping toward the sensor, a pipe lying across the rail, a canted track. In every synthetic scene where the branch
fired (30 rejections in 558 scenes), the rejected cluster was the real object; it never rejected anything else.**
The ride gain reproduces exactly (chunked gate alarm events 23 → 21, alarm frames 111 → 109, STOP episodes 26 → 26; continuous replay STOP rows 120 → 116, 0 added; every per-frame row equal to the author's archive), but the user's priority is
detection range and accuracy, and every lost or delayed true STOP is blocking.

The mechanism is the one the 2026-10-20 review found and amendment 1 patched in-sample: at 30–50 m the low cluster
of an object standing against the rail holds only its front face's lower rings (3–4 returns); the object's real top
lies **outside the cluster's box** (beyond it along the track), so the "uncapped top" the rule compares with
`H + 0.03` is a front-face return 1–3 cm above the head, not the object's top; the top surface (returns within 2 cm
of that one return) is a single return, so it is "0 m wide"; and amendment 1's "face toward the sensor" test only
fires if another return lies within **2 cm laterally** below it. That holds on the ray caster's ideal azimuth grid
(all 128 rings on one grid) and fails on the real Pandar128, whose rings each sit on their own azimuth phase
(measured below), and on any face that is not a vertical plane square to the sensor.

## 2. Findings, ranked

| # | Severity | Finding | Reproducer |
|---|---|---|---|
| F1 | **BLOCKING** | **With the real sensor's per-ring azimuth phases, the organizers'-size box (0.3 × 0.3 m) 3–5 cm above the head on the right rail is made weak; 3 STOP frames lost and first STOP 34.8 → 32.4 m** (3 scenes of the review's own `approach_bed` family re-run with measured phases: 709 → 700 frames; the author's `ext_sizes` geometry, δ 0.03 / 0.05: 287 → 281, first STOP 34.8 → 32.4 in 2 scenes). Random phases (uniform ±0.05°): a 4 m object **10 cm** above the head, first STOP 36.4 → 35.6 m (`azoff`: 827 → 816, 5 scenes later). Picture: [pictures/apb_meas36_f27_cand.png](pictures/apb_meas36_f27_cand.png) — box, front face and top-face returns plainly visible; footprint 5 returns, top one at h 0.160, its lateral neighbours below are 5.8 cm away (> 0.02), H 0.177 → rejected. | `run_attack.sh control\|cand <out> apb_meas [--trace]`, `cmp.py`; families `ext_meas`, `azoff` |
| F2 | **BLOCKING** | **On the ideal grid too, shapes without a square vertical front face are made weak:** a 1 m ramp rising toward its far end with its top **10 cm** above the head, first STOP 33.2 → 32.4 m; the same ramp 5 cm above, 33.2 → 32.4 m; a 0.3 m pipe lying across the right rail 5 cm above the head, STOP frames 16 → 10 (lost at 39–34 m). `shapes`: 1,075 → 1,067, 2 scenes later. Pictures: [ramp](pictures/shapes52_ramp_d010_f25_cand.png), [pipe](pictures/shapes48_cyl_y_f24_cand.png). | `run_attack.sh … shapes` |
| F3 | **BLOCKING** | **Canted track (left rail 10 cm higher), box 10 cm above its own (higher) rail head:** STOP frames 17 → 13 (seed 0) and, with another noise seed, first STOP 38.0 → 36.4 m (seed 303). H is taken from the lower rail (0.147–0.150) while the cluster's footprint top is a front-face return (0.163–0.174). Picture: [pictures/cant21_high_rail_d010_f26_cand.png](pictures/cant21_high_rail_d010_f26_cand.png) — the box's front face is a visible column of returns. | `run_attack.sh … cant`, `… seeds` |
| F4 | HIGH | **The losses are per-frame random, not one unlucky seed, and are all the switch's.** 6 losing configurations × 5 noise seeds: the branch rejects the target in 9 of 30 approaches, 21 STOP frames lost (1 gained), first STOP later in 6 (up to 2.4 m). The candidate with `rail_head_bounded: false` equals v1.2.0 in 30 / 30 of these scenes (matched rows and every gauge detection). | `run_attack.sh control seeds`, `cand seeds --trace`, `cand seeds_off` |
| F5 | HIGH | **The author's synthetic evidence barely exercises the rejecting path, and its sensor model is the one case where amendment 1 works.** In the review's `approach_bed` family (48 scenes; the author's own trace: 1 rejection) the branch rejects a cluster **once** (reproduced: that one rejection is the target box itself, 5 cm above the head, at 48.4 m; no frame lost only because the track survived). My 108 `fine_delta` scenes (δ 0–6 cm, ideal grid): 0 rejections. Set O, `doubleT_obstacle`, the four empty recordings, curves (R 800/2000 m), moving objects, two-object scenes and the Falcon-like raster: 0 rejections of a real object, but also 0 or 1 rejections at all — "no loss" there is non-regression, not safety. Amendment 1 was designed and checked on 3 failing scenes of the same ideal-grid caster (in-sample). | `cmp.py` summaries in `raw/attack_summary.txt` |
| F6 | MEDIUM | **Root cause unaddressed: the comparison height is not the object's top.** `rail_reference_check` uses the max of returns inside the cluster's own x/dy box below `foot_max_top`; the object's upper part beyond the box (its top face, the far edge of a ramp, the crown of a pipe) is invisible to the test, so `top ≤ H + 0.03` holds for objects 5–10 cm above the head. The narrow-top test (≤ 0.10 m) is defeated by sparse sampling (one return within 2 cm of the max), and the face test is a geometric coincidence of the caster. | `resense/lowobj.py:410-427` (`61b6e1a`), traces in `raw/` |
| F7 | INFO | **Code = README** in every other respect: conditions 1–8 as stated; numpy path only (no native counterpart: `rail_reference_check` is pure Python, one call site `detector.py:409`); class default = both YAMLs (`from_yaml` equal, `sync_params.sh --check` passes, YAMLs byte-identical). "Subset of the pre-repair rule's rejections": true by construction (the code checks `height_max < all-returns line + 0.01`, which is 0acb18c's rule, `local_rail_exclude_low` was false there) and confirmed on every new rejection I traced (30 synthetic, 7 `doubleT_platform`, 25 on the ride in 18 frames — 0 violations under either definition, 0 clusters v1.2.0 rejects and the candidate keeps). It is not a safety argument: that pre-repair rule is the one B1 found unsafe. | `attack.py --trace`, `ride_trace.py` |

## 3. Re-derived author rows

| Author row | My result | How |
|---|---|---|
| A1 `approach_bed` 831 → 831 | **831 → 831**, 0 lost, branch fires once (on the target) | my own harness `attack.py --family apb` (re-creation; control rows equal the author's archived control rows 45 × 48), traced == plain 2,160 / 2,160 |
| positive control | rejected completion `a77d884`: **831 → 762, 69 lost in 23 scenes, 15 later, 59 rejecting frames** = the 2026-10-20 review's numbers exactly | same harness and comparator |
| A2 review's 13 controls | **13 / 13 pass** on candidate and control; **13 / 13 fail** on `a77d884` | `review_findings_checks.py` unchanged |
| A4 `tests/test_f1a_bounded.py` | 53 / 53 pass on the candidate; does not collect on v1.2.0 (imports `rail_head_top`) | pytest |
| B1 set O | **1,510 / 1,510 rows identical** (450 STOP rows), branch fires 0 times | `replay.py --full`, `rows_cmp.py`, `ride_trace.py` |
| B2 `doubleT_obstacle` | **201 / 201 identical** (193 STOP rows), 0 firings | same |
| B4 five empty recordings | identical except `doubleT_platform` (168 rows differ from row 31, 7 rejections in 4 frames, 0 STOP either side, 2 CAUTION rows fewer) | same |
| author's archived gate rows | my fresh replays equal the author's archived per-frame gate rows **exactly** on all 7 non-ride recordings, both sides (3,998 rows each) | field-by-field compare |
| C1 ride chunked gate 23 → 21 events, 26 → 26 episodes | **23 → 21 events, 111 → 109 alarm frames, 26 → 26 episodes, advisory 4,764 → 4,759**; 0 STOP rows added, removed piece 1 row 1265 and piece 4 row 80; all 8 × 2 pieces' per-frame rows **equal the author's archived rows** | `ride_gate.py` (gate's own split, `eval_real.run_piece`, `recording_entry`) |
| C2 ride continuous: STOP rows 120 → 116, 0 added | **120 → 116**, removed rows 2670, 2677, 4153, 4154, **0 added**, episodes 26 → 26; rows equal the author's archive on both sides; traced == plain 11,271 / 11,271; 25 new-branch rejections in 18 frames (2668–2676, 4148–4155, 5709–5711), uncapped top − H p50 1.6 cm, max 2.6 cm; ride archive SHA-256 verified on intake | `replay.py --full` both sides, `rows_cmp.py` |
| D1 Falcon 4,443 rows | **not re-run** (disk); a Falcon-like raster in my caster: 8 scenes, 0 rejections, 252 = 252 | `attack.py --family falcon` |
| D2 X3 | **not re-run** (disk / time) | — |

## 4. What I checked and how

* **Code** (`git diff 3b73bbe 61b6e1a -- resense configs ros2_ws native`): read line by line against README §rule and
  PROTOCOL §2 / amendment 1 — finding F7. Config: class default vs `configs/default.yaml` vs ROS `detector.yaml`
  (`DetectorConfig.from_yaml(...).lowobj == DetectorConfig().lowobj`, `cmp`, `sync_params.sh --check`).
* **Instrument checks.** `rc2.py` (my extended caster) equals the repo's `raycast.frame` bit for bit on 3 scenes
  (`rc2_equiv.py`; a 1 cm box move is detected). My re-created `approach_bed` and `ext_sizes` control rows equal the
  author's archived control rows. `cmp.py --selftest` (self-comparison clean, injected loss found) on every family.
  Positive control on a known loss: `a77d884` reproduces the review's 69 lost frames. Traced == plain: `apb` 2,160
  frames; all 7 recordings (after removing the wall-clock latency budget message — my first comparator flagged 50
  `doubleT_platform` rows whose only difference was "latency p95 106 ms over the 100 ms budget"; corrected).
  Attribution: switch off == control in 30 / 30 seed scenes.
* **Labels traced, not inferred.** Each new-branch rejection is identified at the call by evaluating v1.2.0's own
  `rail_reference_check` on the same arguments (control worktree's `lowobj.py` loaded by path); "target" = within
  the match window of the object. 30 / 30 synthetic rejections are on the target.
* **Real azimuth phases** (`az_phase.py`): per ring, the azimuth phase modulo the 0.1° column step of returns at
  25–80 m (1 cm quantisation ≤ 0.023°). `doubleT_obstacle` frames 0 and 100: each ring has a stable phase
  (concentration R p50 0.96, identical between frames) but the rings do not share one (resultant across rings 0.06;
  phases spread −0.042 … +0.044°). Positive control: the caster's grid gives resultant 1.00. The 67 measured ring
  phases (rings 19–85, the ones that reach 25–80 m) are in `az_phase_measured.json`.
* **Ride:** 221 splits cached by `scripts/cache_extended_ride.py` (archive SHA-256 verified); continuous `replay.py --full`
  both sides plus a traced candidate (`ride_trace.py`); chunked `ride_gate.py` both sides (`raw/ride_raw.tar.xz`).
* **Raw data looked at:** pictures of the four losing mechanisms (§2) with the footprint returns printed
  (`pic_frame.py`).
* **Physical plausibility:** objects 0.3 m wide / 0.3–4 m long, tops 3–10 cm above a 0.18 m-raised head, approach
  0.8 m per frame (8 m/s); losses at 31–39 m, first-STOP delays 0.8–2.4 m (1–3 frames). All in range.

## 5. Attack families (control v1.2.0 vs candidate, per frame; `raw/attack_summary.txt`)

| family | scenes | STOP frames ctrl → cand | lost | later first STOP | new-branch rejections (on target) |
|---|---|---|---|---|---|
| `apb` (review's approach_bed, ideal grid) | 48 | 831 → 831 | 0 | 0 | 1 (1) |
| `apb_meas` (same, **real ring phases**) | 48 | 709 → 700 | 9 | 3 | 3 (3) |
| `ext_meas` (author's ext_sizes geometry, real phases, δ 3–15 cm) | 48 | 287 → 281 | 6 | 2 | 2 (2) |
| `azoff` (measured + random phases) | 64 | 827 → 816 | 11 | 5 | 6 (6) |
| `fine_delta` (δ 0–6 cm, ideal grid) | 108 | 444 → 444 | 0 | 0 | 0 |
| `shapes` (yaw 20/45°, ramp toward / away, pipe along / across) | 56 | 1,075 → 1,067 | 8 | 2 | 4 (4) |
| `two` (second object other rail / both rails / region edges / four corners / pipes on both heads) | 24 | 273 → 273 | 0 | 0 | 1 (1) |
| `cant` (5 / 10 / 15 cm) | 36 | 336 → 332 | 4 | 0 | 2 (2) |
| `curve` (R ±800, ±2000 m) | 32 | 515 → 515 | 0 | 0 | 0 |
| `moving` (sliding onto the rail, fast approach, receding) | 16 | 272 → 272 | 0 | 0 | 1 (1) |
| `falcon` (Falcon-like raster) | 8 | 252 → 252 | 0 | 0 | 0 |
| `empty` (6 worlds incl. cant) | 6 | 0 detections both | — | — | 0 |
| `seeds` (6 losing configurations × 5 seeds) | 30 | 409 → 389 | 21 (1 gained) | 6 | 9 (9) |

Every lost frame and every later first STOP above is a real object's. 0 rejections violate the pre-repair condition.

## 6. Not checked / limits

* Falcon whole recording (4,443 rows) and X3 were **not re-run** (disk allowance; ride cache took priority). The
  author's archived Falcon rows show 0 changed fields; I did not re-derive them.
* My scenes are synthetic first-return geometry (no dual return, no beam divergence, no motion distortion); the
  real phase table is from one recording's 67 far-reaching rings. Real-world frequency of these objects unknown.
* Moving objects other than along / onto the rail at constant speed, two-object configurations beyond the six
  tried, and curves with cant combined were not tried.
* The ride is the design set and acceptance set (author's limit, unchanged).

## 7. Reproduce

```bash
# worktrees /home/user/wt/{control,cand,rejected} = 3b73bbe / 61b6e1a / a77d884, each with scripts/build_native.sh
D=docs/evidence/f1a_bounded_review_2026-10-21
$D/run_attack.sh control <out> apb_meas; $D/run_attack.sh cand <out> apb_meas --trace
python3 $D/cmp.py <out>/apb_meas-control.json <out>/apb_meas-cand_trace.json --selftest
RESENSE_REPO=<cand> python3 $D/pic_frame.py apb_meas 36 27 frame.png            # the F1 frame
python3 $D/az_phase.py /data/cache/doubleT_obstacle 0 100                          # real ring phases
# recordings / ride: replay.py --full per side, ride_trace.py (traced cand), rows_cmp.py; ride_gate.py per side
```
