# Independent review: Falcon far range 1.3 (`claude/falcon-far-range-1.3`, head `ff59349`, detector `0eb4dda`)

Reviewer: a fresh session dispatched by the captain, 21.10. I did not write the code and changed no file under
`resense/`, `native/`, `configs/`, `ros2_ws/` or `tests/`. Nothing was run on G3. Control: v1.2.0 `3b73bbe`
(detached worktree). Candidate: `0eb4dda` (detached worktree; `git diff 0eb4dda ff59349 -- resense configs ros2_ws native`
is empty). Python 3.13, numpy from `pip install -e ".[dev]"` (the author used 3.12); every run below names its checkout
through `RESENSE_REPO`, and the loaded native library was checked to come from that checkout.

## Verdict: **ACCEPT WITH CONDITIONS**

The range gain is real, comes from the person, and holds on every scene I built. No v1.2.0 STOP is lost or delayed in
any test: the full recording, 6 start frames, 82 edited scenes (164 runs), and the injection matrix on fresh seeds 40 and 41.
Pandar is unchanged. The false-alarm rows improve. Two things are reported in a way that overstates the result, though,
and one behaviour change is not measured by any of the author's criteria: the candidate outputs **GO while a visible
person stands inside the clear distance it reports** (30 frames on the real recording, 0 for v1.2.0; 827 against 92
frames over my scenes; 324 against 0 in the fresh-seed matrix). This is not a lost STOP, so it does not block under the user's rules. It is, however, a safety-relevant regression in what the
train is told, and it needs to be fixed or explicitly accepted before the switch ships (condition C1).

Conditions:
* **C1** (finding F1): fix or accept the GO-with-person-inside-the-clear-range exposure. A fix must not cost STOPs. Candidate
  fix: while a far axis is active, cap the monitored/clear range at `far.valid` where the near model's laterals beyond it
  disagree with the far line by more than the gauge tolerance. Re-run `person_frames.py` and the scene table.
* **C2** (F2): restate the range result as "first STOP 149.5 m (a 0.5 s blip, then no STOP for 11 s); STOP held from
  129.5 m (v1.2.0: 123.0 m)", and say the blip depends on the detector state (it appears in 4 of 6 start frames).
* **C3** (F3): correct the turnout residual. It is not "shared with the near model": the candidate trusts the wrong
  straight line to about 390 m, where v1.2.0 trusts its near model only to 107–175 m.

## Findings (most severe first)

| # | severity | finding | reproducer |
|---|---|---|---|
| F1 | **High** (not blocking under the stated rules: no STOP lost) | **GO with a visible person inside the reported clear and monitored range.** Real recording: 30 frames (2660–2848) in which the candidate says GO while the main person stands on the track centre (lateral −0.2 to −0.3 m) at 138.6–162.3 m. That is inside both `clear` (149–167 m) and `monitored` (149–167 m). The person returns 16–25 raw points per frame and stands 1.4–1.8 m tall, so the person is in view. v1.2.0: 0 such frames; it said CAUTION in all 30, because of false warnings on the 105 and 115 m left-side structures, which the candidate correctly removes. Cause: in every one of the 30 frames the person is beyond the far axis' `valid` (122–139 m). From there to the near model's `axis_valid` (up to 167 m) the corridor uses the near model's laterals, which are about 2 m off the track at 150 m. So the person is outside the corridor, but the clear distance runs past them. `detector.py` `_corridor`: `axis_valid = max(axis_valid, far.valid)`. The latent false clear exists in v1.2.0 too; the candidate turns it into GO. Over the 82 scenes: 827 frames against 92, worse in 34 scenes. Injection matrix, fresh seeds 40 and 41: 324 frames against 0 (static 150 m targets, receding, lateral and crossing walks). The 19.10 axis had it too (7 frames). The README presents the CAUTION share falling from 0.685 to 0.183 as a pure gain; part of that fall is these frames. | `scripts/person_frames.py full/base.jsonl full/cand.jsonl` → `results/person_frames_fresh.json`; per-frame raw check in this README §3.2 |
| F2 | Medium (reporting) | **The 149.5 m first STOP is a 5-frame blip.** It covers frames 2762–2766 (149.7 → 149.2 m). The next STOP comes at frame 2875 (135.4 m), about 11 s later, and STOP is held (≥ 90 % of the next 3 s) from frame 2926, 129.5 m. v1.2.0's STOP is held from 123.0 m. The blip coincides with the far trusted range jumping to 156–159 m (it is 134–139 m in the surrounding frames). It depends on the detector state: replays started at frames 0 / 600 / 1800 / 2100 give 149.7 m, starts at 1200 / 2400 give 135.0 / 135.4 m. The held STOP is stable: 127.4–130.2 m for the candidate against 114.4–123.0 m for v1.2.0, a gain of 7–15 m over 6 starts. The README's "149.5 m (≥ 90 % STOP from there)" uses a 90 % share over the whole rest of the recording (1,680 frames), which hides the 11 s gap. The README calls the 19.10 candidate's equivalent "1 frame; held from 127.1 m". | `results/starts.txt`; `scripts/evalrows.py full/cand.jsonl` (held_stop_x); `scripts/starts.sh` |
| F3 | Medium | **Turnout or crossover: wrong trust extended to about 390 m, not "shared".** With straight structures on both sides and the track curving away between them, the new axis trusts a straight line out to 377 m in my tracker probe W (wide walls at 3.5 m, 19.10 axis capped at 175 m) and to 392 m in the author's own case K. v1.2.0 trusts its near model to 107–175 m only. The README (§4) calls this an "unverified residual shared with the 19.10 axis and the near model". It is shared within 175 m; beyond that, only the candidate claims to monitor a wrong line. Consequence: false clear claims, and possible false STOPs on objects ahead on the straight branch. No lost STOP, because v1.2.0 does not see that far either. The physically consistent scene versions on the real recording (structures removed where the curved track passes) gave no lost STOP (scenes `turnout_*`, `wide_turnout_*`). | `scripts/tracker_probe.py --out probes.json` (cases `W_*`) → `results/probes_cand.json`; author `neg_controls.json` case K |
| F4 | Low | **Added false STOP episodes in edited scenes, all on the 115 m left-side structure.** +1 in `curve_all_xc150_R300_d+1` (frames 2723–2725, while the far axis is held and decaying 10 m per frame and its `valid` passes below 115 m). +2 in `row_offset_+0.8`, where the right column row is moved into the clearance envelope, which is not a physical scene. v1.2.0 STOPs on the same structure in other frames (29 frames on the real recording). Over all scenes, false episodes fall from 141 to 82. These scenes are synthetic and are not part of the A4 bound (the Falcon recording, the ride and the five empty Pandar recordings). | `results/scenes_compare.txt`; `scripts/evalrows.py scenes/<scene>__wt_cand.jsonl --spec specs/<scene>.json` |
| F5 | Low | **In-sample design, out-of-sample only in the target noise.** A2, A3 and A5 were each made after seeing the real recording's false episodes or its first STOP. A5 in particular came after A3 left the first STOP at 127.07 m (= v1.2.0), and it changed the vote that yields 149.5 m. The "fresh seeds 20–22" matrix injects into the same recording's frames, so it is not out-of-sample for the scene. My scene edits are the only geometry the design did not see; they show no lost STOP, a smaller gain than on the real scene, and no gain at all when the far axis cannot form (curves from 120 m: candidate = v1.2.0 row for row in the person rows). | `results/scenes_compare.txt` |
| F6 | Note | Stale comments in `config.py`: `axis_second_tube` says "about its own robust line" (since A2 it is the primary line); `axis_history_frames` says "the used support is the second-highest aged value" (since A5 it is the vote). The acceptance test `test_stable_switch_is_off_by_default_and_enabled_with_the_profile_switch_only` keeps its name, but now that the switch is on by default its first assertion is a disjunction that holds either way. | `git diff 3b73bbe 0eb4dda -- resense/config.py`; `tests/test_farrange.py:379` |
| F7 | Note | Switching `with_falcon_profile` on also ships 19.10's C6 (`far_min_height` 0.3, `far_max_length` 4.0) and the 400 m crop under the Falcon profiles. The README mentions the switch but not that C6 (in-sample, 19.10 review B2) comes with it. Where the far axis never forms, the candidate and v1.2.0 still differ through C6. Example: synthetic outer-wall scenes have more STOP frames with an unassociated detection, 302 → 315. | `results/cfg_wt_*.json`; `results/scenes_compare.txt` (`curve_all_xc120_*`) |

## 1. Diff and configuration (task 1)

`git diff 3b73bbe 0eb4dda -- resense configs ros2_ws native`: `farline.py` (+195: `_side_bins` split out of `measure`;
`_rejected_run_start`, `_second_tube`, `measure_stable`, `FarAxisTracker._update_stable`), `config.py` (8 keys; two defaults
switched on), `detector.py` (passes `dt`), and 3 YAML lines in each copy. Read line by line against README §2 and PROTOCOL A1–A5:

* **C7** is as described: the offset is the mean residual against the primary line, kept from the near end while max |dev| < T
  and rms ≤ 0.25. The contradiction is the last kept bin. The support is contiguous (gap ≤ 40 m). The drift test covers the last 3 bins.
  The offset is free, so any row parallel to the primary inside the 1.2–4.0 m band confirms it. My scenes `row_offset_±0.4`
  and `row_step_0.45_from150` show this does not cost STOPs.
* **C8** is as described: confirmations and contradictions are aged at 25 m/s using the real `dt`. A level is used if it is the farthest level reached by
  ≥ 2 frames and by more frames than contradict below it. This frame's contradiction and divergence cap at once. A frame that fails
  measurement decays the support by 10 m per frame. The 1 s window uses `axis_frame_dt` regardless of `dt`.
* **C9**: without a two-sided support, `_update_stable` returns None (the near model, as in v1.2.0), unless a route section is declared.
* Two fitted walls no longer have the 0.002 slope-agreement test. Only the divergence cap `join + T/|Δs|` remains, for the current frame.
  A tube-confirmed one-wall axis counts as two sides: kink limit 0.01 instead of 0.006, and no one-side slope term in sigma.
  Probe S (wall and row both skewed by 0.003 / 0.006): fail-safe by the protocol tolerance (error 0.44 / 0.51 m); 0.009 is rejected.
* **Settings agree.** I resolved the effective config of every profile × both YAML copies × the class default in both checkouts
  (`scripts/cfgdiff.py` → `results/cfg_wt_*.json`). The class defaults, `configs/default.yaml` and
  `ros2_ws/.../detector.yaml` hold identical `farrange` values. `manual` and `pandar128` differ from v1.2.0 only in the
  `farrange` section, with `enabled` False. `falcon_ros` and `falcon_native` additionally get `enabled`, the 400 m crops and C6 (F7).
  The only reader of `with_falcon_profile` is `sensor_profiles.apply_sensor_profile`, gated on `range_model == "falcon_prime"`.
* **Pandar rows** (gate machinery `eval_real.run_piece`, default config; `scripts/pandar_sample.py`, `scripts/rowdiff_pandar.py`):
  `doubleT_obstacle` 201, `roundT_doubleT` 252, `doubleT_platform` 345, and three ride splits (`new_data_30`, `_58`, `_200`, 153
  frames). **951 / 951 rows identical** on every field except timing. Positive control: the candidate with `farrange.enabled=true`
  forced under the default config changes 151 / 201 rows of `doubleT_obstacle`, so the comparison does detect a change. Not run: the other
  three recordings, set O, set F and the other 218 ride splits (the author's full gate is not re-derived here).
* Unit tests: `tests/test_farrange.py` 19 / 19 pass on `0eb4dda`.

## 2. Re-derivation on the real recording (task 2)

Fresh Falcon cache (4,443 frames, 89 / 89 decode checks identical). Full replays with the author's `run_far.py`:

| run | decisions G/C/S | STOP eps | eps without person | first STOP main person | held from (≥ 90 % of next 3 s) | GO with person inside clear |
|---|---|---|---|---|---|---|
| v1.2.0 `3b73bbe` | 13 / 3,043 / 1,387 | 8 | 3 (25–28, 125, 2312–14) | 127.1 m (frame 2950) | 123.0 m (2988) | 0 |
| **candidate `0eb4dda`** | 2,148 / 811 / 1,484 | **5** | **0** | **149.5 m (2762, 5 frames)** | **129.5 m (2926)** | **30** |
| positive control: v1.2.0 + `with_falcon_profile` (= 19.10 axis) | 1,420 / 1,635 / 1,388 | **9** | 0 | **146.3 m (2787, one frame)** | 123.0 m | 7 |

* **Positive control reproduced:** the 19.10 candidate's 9th episode and its one-frame 146.3 m STOP. The branch with
  `axis_stable=false` equals it row for row (4,443 / 4,443).
* **Identity with the author's archive** (`raw/replays.tar.xz`): decision, detections, warnings, nearest, clear and monitored are identical on 4,443 / 4,443
  rows for v1.2.0, the candidate and the 19.10 run. The traced candidate equals the plain candidate on every field except timing.
* **Independent evaluation** (`scripts/evalrows.py`): my own code, per-detection association to the reviewed N2 anchors (±2.5 m
  along, ±1 m lateral). It gives the same episode counts and false episodes as `falcon_eval.py`. Per detection, the candidate's STOP
  frames with an unassociated detection are 21 (v1.2.0: 49). 20 of them are the near-field objects at 7–41 m in frames 4294–4375, the same in both. One (frame
  4221) is the 115 m structure inside a person episode (v1.2.0 has it in 29 frames).
* **The returns are the person** (CLAUDE.md item 4). At every candidate episode onset (2762, 2875, 2885, 2906, 2926), the STOP detection
  is a vertical column of 18–29 raw points, 1.4–1.65 m tall and 0.7–0.9 m wide, on the track centre. The same box has 0 points in background frames
  1400 and 600 ([figs/person_stop_onsets.png](figs/person_stop_onsets.png)). Plausibility: 149.7 → 129.4 m in 16.4 s is
  1.24 m/s, a walk.
* **Start-frame robustness** (`scripts/starts.sh`, plain replays from frames s to 3300):

| start | v1.2.0 first / held | candidate first / held | episodes v1.2.0 / candidate |
|---|---|---|---|
| 0 | 127.3 / 123.0 | 149.7 / 129.5 | 8 / 5 |
| 600 | 127.1 / 120.5 | 149.7 / 130.2 | 9 / 5 |
| 1200 | 127.3 / 114.4 | 135.0 / 129.8 | 11 / 3 |
| 1800 | 127.3 / 122.4 | 149.7 / 129.5 | 9 / 4 |
| 2100 | 124.0 / 122.3 | 149.7 / 129.8 | 8 / 4 |
| 2400 | 123.4 / 120.5 | 135.4 / 127.4 | 7 / 4 |

  The candidate is never worse. 0 false episodes in every start.
* Timing (not a criterion; concurrent runs on 4 shared cores, so noisy): detector p50 / p95 17.9 / 30.6 ms for v1.2.0, 19.6 / 29.4 ms for the candidate.

### 3.2 The GO frames of F1, checked on raw points

All 30 frames listed in `results/person_frames_fresh.json`: person centre (N2 anchor) at 138.6–162.3 m, lateral −0.22 to −0.29 m. Raw points in a
2 × 1.2 m box: 16–25 (median 21), top 1.40–1.79 m above the rail head. The candidate's `clear` is 149.0–167.0 m and `monitored`
149.0–167.0 m, both ≥ the person's distance. The far axis' `valid` is 122–139 m, so the person is beyond it in 30 / 30 frames. v1.2.0's
decision is CAUTION in 30 / 30. Its warnings in those frames are the 105 / 115 m structures, not the person.

## 3. Generalisation: scenes the author did not see (task 3)

**Tool** (`scripts/scene_run.py`, specs from `scripts/make_specs.py`, 82 scenes × 2 checkouts). Real Falcon frames are edited
in the raw frame before the detector, with point groups defined by the lateral to the track reference: centre |lat| ≤ 1 m (rails, bed, people,
injected targets), left > 1 m, right −4.5…−1 m (this track's column row), far right, and high > 3 m.
* **warp** bends the chosen groups along a curve from Xc.
* **outer_wall** adds a ray-consistent opaque face 2 m outside the curve. Every ray whose return lies behind it returns on the face instead.
  The closed form was checked against a sampled loop, which agrees within its 0.5 m sampling (`scripts/check_outer.py`).
* **clear_envelope** removes structures the curved track would run into.
* **skew** and **shift** move structures.
* **scroll** is a moving scene.
* Targets use the author's ray-cast injector.

I looked at the edits ([figs/edits.png](figs/edits.png)). Limitations:
* A warp keeps the real rays' angular density. It does not invent rays that had no return.
* The scrolled scenes thin out the far field and cannot represent a moving train. Speed is therefore judged from the tracker probes.
* Windows start cold at frame 2400 (person 191 → ~100 m) or 1290 (empty frames). The `plain_real` window gives the same picture as the full run:
  first / held STOP 123.4 / 120.5 m for v1.2.0 and 135.4 / 127.4 m for the candidate.

Full table: [results/scenes_compare.txt](results/scenes_compare.txt) (and `results/scenes.md` / `scenes.json`). Summary:

| scene family (what it probes) | lost or delayed STOP vs v1.2.0 | added false episodes | far axis | notes |
|---|---|---|---|---|
| `curve_all` Xc 120/150/175/200/245 m, R 300/1000, both directions, outer wall (curve right after the last confirmed bin, in the 195–245 m gap; a wall on the curve) | **0 / 15** | +1 (Xc 150, R 300, left; F4) | none for Xc 120; otherwise valid ≤ 184 m | Xc 120: the candidate = v1.2.0 (no far axis). Both have 14–24 false episodes on the synthetic outer wall. Gains elsewhere: held STOP 120–122 → 122–131 m |
| `left_straight` (one straight boundary, the track curving away) | 0 / 3 | 0 | 9 frames at Xc 100 | as v1.2.0 at Xc 100 |
| `row_other_track` (the row belongs to another track and stays straight) | 0 / 3 | 0 | 0–864 frames | Xc 130: no far axis; equal |
| `turnout` and `wide_turnout` (both boundaries straight, only the track bends; structures in the way removed) | 0 / 16 | 0 | up to 186 m | no lost STOP; GO-inside-clear 0–43 frames (F1) |
| `skew_structures` 0.003 / 0.006 | 0 / 2 | 0 | ≤ 166 m | |
| `row_offset` ±0.4, +0.8; `row_step` 0.45 m from 150 m (a parallel but offset second side) | 0 / 4 | +2 (+0.8, non-physical; F4) | | the offset is free by design; no loss |
| `obj120/140/160` on a straight track and on curves from 100 / 130 m (object on a curved continuation, with a wall on the curve) | **0 / 15** | 0 | none on the curves | on the curves the candidate = v1.2.0. Neither STOPs the 140–160 m person on an R 300 m curve, or the 160 m person on any curve: a shared limit. Straight: 120 m STOP frames 61 → 146; 140 m 0 → 15 |
| `edge` lateral 0.6 / 0.75 / 0.9 m at 60–140 m (the strict gauge shrinks by sigma under the far axis) | **0 / 15** | 0 | | STOP frames equal at 60–100 m; better at 120–140 m (e.g. 120 m / 0.6 m: 41 → 123) |
| `moving` v 0 / 10 / 25 / 30 m/s (scrolled) | 0 / 8 | 0 | none at 25–30 m/s | the edit thins the far field; see the probes below |

Over all 82 scenes: **0 lost or delayed STOPs**. False episodes: 141 for v1.2.0, 82 for the candidate. GO with the target inside the clear range:
92 against **827** frames (F1).

**Tracker probes** (`scripts/tracker_probe.py`, `FarAxisTracker` alone, the author's synthetic helpers, protocol fail-safe
tolerance; `results/probes_cand.json`):
* Positive control: the author's case J comes out fail-safe here too.
* **Speed** (the history assumes 25 m/s): a curve starting in a 55 m primary gap approaches at 0 / 10 / 25 / 30 / 40 m/s, R 300 / 1000,
  curve start 230 or 175 m. All fail-safe, maximum error 0.14 m, and `valid` stays below the curve start. With dt = 0.2 s at 25 and 30 m/s, also fail-safe.
  "Speed unknown" does not change anything: the ageing always uses 25 m/s and never the ego speed. Above 25 m/s, older supports
  are over-estimated by at most (v − 25) × 1 s, which the 17 m lead and the sigma cut absorb in these probes.
* **Row of another track** (`O_*`): fail-safe.
* **Skewed pair** (`S_*`): fail-safe.
* **Wide straight boundaries with the track curving between them** (`W_*`): not fail-safe; `valid` reaches 377 m (F3).

## 4. Conditional route-map variant (task 4)

`map300` / `declared_straight_to` is presented as conditional everywhere I looked: README table column and §3, PROTOCOL §2 / §4 / A4.2, and the
commit messages `6ee469c..ff59349`. No file outside the evidence folder was changed by the branch except the detector, tests and YAMLs. The
`declared_straight_to` default is 0 in the class and in both YAMLs. **No finding.**

## 5. Injection matrix on fresh seeds 40, 41 (task 2, matrix rows)

The author's `matrix2.py` with my seeds 40 and 41 (never used by the author), both checkouts, 136 cases each, `--check-prefix`
0 / 310 mismatches for both. The author's `matrix_compare.py` → `results/matrix_compare_s40_41.json`: **criteria 7, 8, 9 and 10 all
pass, no failing case.**
* Approach from 400 m, first STOP: v1.2.0 109–117 m, candidate **133–141 m** on all 16 in-gauge target × seed cases, for gains of 22–29 m.
  Outside control: no STOP in either.
* Static 150–350 m: neither checkout STOPs any target at any static range (stop fraction 0 for both).
* F1 reproduces on injected targets (`scripts/matrix_go.py` → `results/matrix_go_s40_41.json`). Frames with GO while an in-gauge target is
  inside the reported clear and monitored range: v1.2.0 0 in every mode; the candidate 231 frames in 16 / 18 static-150 m cases, plus
  M2 receding walk 32, M4 lateral walk 19, M6 crossing 39. The 1 m cube and the 2 m boxes standing at 150 m are not STOPped by
  either checkout. The candidate says GO in 93–144 of their 150 frames, against 0 GO frames for v1.2.0; in 11–24 of those frames the clear distance runs past the box.

## 6. What was not checked

* The full Pandar gate (set O, set F, the other three recordings, 218 of 221 ride splits) and X3. I relied on the author's runs for those and
  re-derived only the 951-frame sample and the config-level isolation.
* The ROS node path (the author's `node_check.py`) was not re-run.
* Moving-train behaviour on real data: none exists. My scrolled scenes are weak, so the speed conclusion rests on the tracker probes.
* The walk control and the doubt-model runs were not re-run.
* Real curves: all curve evidence is synthetic (warped real frames or synthetic boundaries).

## 7. Reproduce

```bash
# venv as the task: pip install -e ".[dev]"; pip install rosbags==0.11.5; scripts/build_native.sh (also in each worktree)
git worktree add --detach ~/wt_v120 3b73bbe; git worktree add --detach ~/wt_cand 0eb4dda
S=docs/evidence/falcon_far_range_review_2026-10-21/scripts
python docs/evidence/falcon_long_range_2026-10-19/scripts/cache_falcon_full.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --out ~/data/falcon
$S/full_runs.sh                       # base, cand (--trace), pc1910, c89, cand_plain  -> ~/rv/full
python $S/evalrows.py ~/rv/full/cand.jsonl; python $S/person_frames.py ~/rv/full/base.jsonl ~/rv/full/cand.jsonl
python $S/make_specs.py ~/rv/specs && $S/scenes.sh ~/rv/specs ~/rv/scenes 4 && python $S/summarize_scenes.py ~/rv/specs ~/rv/scenes --json s.json --md s.md
$S/starts.sh 2; $S/matrix_runs.sh 1 && python $S/matrix_go.py ~/rv/matrix --json matrix_go.json
python $S/tracker_probe.py --out probes.json
RESENSE_REPO=<checkout> python $S/pandar_sample.py --cache <cache> --work <out> doubleT_obstacle roundT_doubleT doubleT_platform new_data
```

Scripts expect `/home/user/rv` and `/home/user/data`; paths are at the top of each script. Raw outputs: `raw/full_replays.tar.xz`
(5 full replays), `raw/scenes.tar.xz` (164 scene runs and their specs), `raw/pandar_rows.tar.xz`, `raw/matrix.tar.xz`, `raw/starts.tar.xz`.

---

# Re-review: revision 2 (`claude/falcon-far-range-1.3` head `aec8b69`, detector `c431b2e`), 22.10

Asked by the captain's session. Its questions, with my answers. The rev-1 section above is kept as history.
`git diff c431b2e aec8b69 -- resense configs ros2_ws native` is empty. Checkout: a detached worktree `c431b2e` with its own
native build. Nothing was downloaded from Google Drive; the Pandar sample reused my existing caches.

## Verdict (revision 2): **ACCEPT WITH CONDITIONS**

Every hard row I re-derived holds:
* **No STOP lost or delayed** against v1.2.0: whole recording, 6 start frames, 82 scenes, and a matrix on seeds 70 and 71, which the author did not use.
* **F1 is fixed as a regression.** The candidate has 0 GO-with-target-inside-clear frames that v1.2.0 does not have, everywhere I looked.
* **The range gain is real and on the person:** held STOP 129.4–135.5 m against 114.4–123.0 m.
* **Pandar is unchanged.**

The one remaining finding (R2-1) concerns the stated turnout residual, which the README calls "physically impossible". It is
reachable. It creates no lost STOP and no false STOP. It is a false-clear claim to about 390 m in a turnout geometry that does not occur in
the data. Condition: correct that README sentence and file the residual. No detector change is required for this lane under the
user's rules.

| # | severity | finding | reproducer |
|---|---|---|---|
| R2-1 | Medium (not blocking: no STOP lost, no false STOP; a false clear claim) | **The C3 guard misses passable turnout openings.** The guard ends a confirming side at a gap ≥ √(2R(d+1.6)) (37–41 m at d 1.9–2.5 m, R 200 m). That formula assumes the diverging curve starts at the gap. A curve starting before the gap only needs the train's envelope to cross the boundary line, which takes an opening of √(2R)·(√(d+1.6) − √(d−1.6)): 21.5–26.5 m at R 200 m and 26.4–32.4 m at R 300 m. Synthetic, physically consistent scenes (the train envelope ±1.6 m is checked to be free of every structure point): a straight dense wall with such an opening on the diverging side and a straight wall opposite. The far axis trusts the straight line to **392 m, error 104–196 m, in 24 / 24 wall cases** (R 200 / 300, d 1.9 / 2.2 / 2.5, Xc 110 / 140, both sides). A 25 m column row at d 2.5 m, R 200 m: 2 more cases fail (valid 372 m). 30 m column rows, which is the real recording's spacing: fail-safe (the support ends before the curve). The README's "physically impossible for R ≥ 200 m under the stated envelope" is therefore wrong. v1.2.0 trusts its near model only to 107–175 m. The real Falcon scene cannot be exploited this way: the right column row stands 1.35–2.2 m from the track, too close for an R 200 m exit without hitting a column. | `scripts/turnout_probe.py --out t.json` (RESENSE_REPO = `c431b2e`) → `results_rev2/turnout_probe_rev2.json` |
| R2-2 | Note | **The union adds points but changes cluster shapes.** Point level: correct, a point takes whichever lateral is nearer the centre, so no v1.2.0 corridor point leaves the corridor beyond `far.valid`. Up to `far.valid` the far line still *replaces* the near laterals, as in rev 1. At cluster level the two hypotheses can merge a person with a wall. Example, start 1800, frames 2704–2705: one 6.4 × 2.9 m detection holding the person (18 points at lat −0.2, up to 1.65 m) and the left wall (15 points at lat 1.2–2.75), centre between them. It STOPs. A merge could also produce a cluster that a size rule rejects, which would lose a STOP. I found none: 0 lost in every test. | `results_rev2/starts_rev2.txt`; the frame check in the item 2 answer |

## 1. F1: union corridor (A6), report cap (A7), report lag (A9 / A10). Is "0 new" right?

* **Whole recording** (`run_far.py` on `c431b2e`, `person_frames.py`): 0 GO frames with the person inside clear and monitored (v1.2.0 0; rev 1 30).
  0 frames where v1.2.0 had a person warning or STOP and rev 2 has neither. First STOP 150.5 m (frame 2756); held STOP 129.4 m.
* **6 starts**: 0 at every start. v1.2.0 has 1 at the 2400 start. Table (my rows reproduce the author's exactly):

| start | v1.2.0 first / held, eps (false), GO-in | rev 2 first / held, eps (false), GO-in |
|---|---|---|
| 0 | 127.3 / 123.0, 8 (3), 0 | 150.5 / 129.4, 13 (0), 0 |
| 600 | 127.1 / 120.5, 9 (2), 0 | 150.4 / 135.4, 8 (0), 0 |
| 1200 | 127.3 / 114.4, 11 (3), 0 | 150.5 / 135.0, 7 (0), 0 |
| 1800 | 127.3 / 122.4, 9 (1), 0 | 150.5 / 129.4, 15 (1), 0 |
| 2100 | 124.0 / 122.3, 8 (2), 0 | 150.5 / 135.5, 8 (0), 0 |
| 2400 | 123.4 / 120.5, 7 (2), 1 | 150.5 / 132.2, 9 (0), 0 |

* **82 scenes** (all re-run on `c431b2e`; v1.2.0 rows are mine from rev 1): GO-inside-clear frames 92 for v1.2.0, **43** for rev 2.
  Per frame and target, **0 rev-2 frames that v1.2.0 does not also have** (`results_rev2/scenes_rev2_compare.txt`). The author's claim is
  right. False episodes 141 → 81. Added only in `curve_all_xc150_R300_d+1` (+1) and the non-physical `row_offset_+0.8` (+2), as in rev 1 (F4).
  0 lost or delayed STOPs, by stop frames, first STOP or held STOP (tolerance 2 frames / 2 m).
* **Matrix, seeds 70 and 71** (mine, not used before): `--check-prefix` 0 / 310 for both. Criteria 7–10 pass. Approach first STOP
  133–139 m against 109–117 m. GO-inside-clear **0 / 0** (rev 1 had 324 on seeds 40 / 41). No case with fewer STOP frames.
* **Is "0 new" the right bar?** Yes, for this lane. The bar asks that the change create no GO-with-target-inside-clear frame v1.2.0 does not have, and
  it creates none. The 43 inherited frames are v1.2.0's near-model false clears where no far axis forms. They should be filed for
  the clear-distance lane, not counted against this change. The positive control is rev 1, which my tools flagged at 30 / 827 / 324 frames.
  A9 / A10 change only the reported `clear` / `monitored`. The author states, and my whole-recording replay agrees, that the decisions and
  detections equal the uncapped A7 build's.

## 2. Range claims and the 13 episodes

* Held STOP 129.4–135.5 m against 114.4–123.0 m at the 6 starts: **confirmed** (table above).
* First STOP 150.4–150.5 m at every start, intermittent: **confirmed**. Start 0: 3-frame episode 2756–2758, then 2–15-frame episodes
  until the STOP is held from frame 2927 (129.4 m).
* **Episodes 8 → 13: all 13 are on the person.** At each onset (start 0: 2756, 2760, 2764, 2768, 2782, 2800, 2809, 2856, 2858,
  2875, 2879, 2902, 2927), the raw points in a 2 × 1.2 m box around the detection number 20–27, stand 1.43–1.67 m tall at lateral
  −0.55…+0.36, and sit 0.0–0.2 m from the reviewed person anchor. The same box holds 0 points in background frame 1400.
  Whole recording (`falcon_eval.py`): 13 episodes, 0 without a person, 0 non-person STOP frames, 0 person-STOP frames lost, CAUTION
  share 0.186. Falcon +5 episodes against the A4 bound of +11.
* **The start-1800 false episode (2704–2705)**: confirmed as the person merged with the left wall (R2-2). The detection centre at
  155.96 m, lat +0.86, has no point within 1 × 0.6 m of it; the box holds the person (18 points, lat −0.2, 156.6–157.2 m) and
  the left wall (15 points, lat 1.2–3, 152.8–159.3 m). It is a STOP while the person really is in the gauge, with a wrong centre. It is not
  a false alarm in substance, though the per-centre association counts it as one. v1.2.0 has 1 false episode at that start too.

## 3. C3 guards

* My probe W and the author's case K: **fail-safe on `c431b2e`.** Tracker probes 40 / 40; the author's negative controls 92 / 92 required,
  and K now has `valid` 142 m, error 0. Speed probes 0–40 m/s: fail-safe.
* **Attack on the stated residual** (tight boundaries ≤ 2.5 m, an opening shorter than the guard's exit length): **not fail-safe**,
  see R2-1. Suggested direction, for the author: use the crossing length √(2R)(√(d+h) − √(max(d−h, 0))) as the gap threshold.
  A side whose boundary is closer than h confirms everywhere, since no train can pass it. Measure what this costs on the real row
  (30 m column spacing, d 1.35–2.2 m), because a stricter threshold may end the right row's confirmation and with it the range gain.
* "The union corridor only adds points": true per point beyond `far.valid`; not a guarantee per detection (R2-2); no loss observed.

## 4. Pandar and configuration

* Effective config per profile × YAML copy × class default (`scripts/cfgdiff.py`): `manual` / `pandar128` differ from v1.2.0 only
  inside `farrange`, with `enabled` False. The new keys exist only as class defaults; neither YAML sets them, so both copies agree.
  Every new code path in `detector.py` is gated on `self.far` / `self._far_axis` / `_union_shift`, which are None without the Falcon profile.
* Rows: `doubleT_obstacle`, `roundT_doubleT`, `doubleT_platform` and the ride splits 30 / 58 / 200: **951 / 951 identical** to v1.2.0 on
  every field except timing (`health.latency_p95_ms` differs in 39 rows). No Google Drive download.
* Unit tests: `tests/test_farrange.py` 21 / 21 pass on `c431b2e`.

## 5. Not checked (revision 2)

The full Pandar gate, set O, set F and X3 on `c431b2e` (the author reports X3 as unverified because of the Drive quota). The node path, the walk control and
the doubt model were not re-run. All curve and turnout evidence is synthetic.
