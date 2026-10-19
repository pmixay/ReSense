# F1 + Falcon false STOPs: handoff (19.10, ~15:10 UTC, stopped on P1's request)

Branch `det/f1-false-alarms` from `main` `aec88d2`. Protocol and amendments 1–8: [`PROTOCOL.md`](PROTOCOL.md).
Independent review 1: [`review/REVIEW_1.md`](review/REVIEW_1.md). No seal, version or shared doc was changed; the
branch's detector files differ from the seal, so `scripts/detector_freeze.py verify` fails until P1 reseals.

## 1. Switches and defaults at HEAD (class defaults = both YAML copies, repo convention)

| switch | HEAD value | what it does | status |
|---|---|---|---|
| `lowobj.local_rail_margin` (F1a) | **0.01** | a low cluster's top must exceed the frame's own local rail-head line (both rails, ±5 m) + margin | see §3: not recommended as is |
| `lowobj.local_rail_cross_tol` (F1a″, am. 7) | **0.04** | rails' lines differ > 0.04 m → the lower line is the reference (review B1 fix) | caused a new false STOP (5714) |
| `lowobj.local_rail_exclude_low` (F1a′, am. 6) | false | rail lines leave out all low clusters' returns | measured: costs the effect |
| `lowobj.local_rail_advisory` (am. 6) | false (= weak mode) | failing cluster advisory `below_rail_ref` instead of weak evidence | measured: costs the effect |
| `lowobj.rail_band_range` / `no_rail_low_within` (F1b / F1c) | 0 / 0 | card tasks (b), (c) | measured, no benefit; off |
| `cluster.mount_cross_tol` (H) + `mount_cross_above_only` (H′) | **0.5** / true | near field: model rail head vs calibrated mount plane differ > 0.5 + 0.05·X → a cluster the mount puts entirely above the envelope top is advisory `height_conflict` | recommended |
| `tracking.settle_min_hits` (S / S2) | 0 (`settle_check_z` false) | long-static track mostly outside the gauge stays advisory | withdrawn (am. 6): can delay a vertical entry |

**Off = `aec88d2`:** every switch 0 → shown identical (all non-timing fields) on the **full gate per-frame** (15,269 rows,
set F equal; code `1144150`), the **whole Falcon** (4,443 rows; code `129415f`) and the **whole ride, one detector**
(code `8c88d5c`; 130 STOP / 30 episodes, 0 transitions). **Not re-shown for HEAD `18ec81d`** (its code paths are all
behind the same `> 0` guards; a gate + Falcon re-run with the switches at 0 is the remaining proof).

## 2. Results against the registered rows

| row | base `aec88d2` | best measured (F1a 0.01 weak + H + S2, `129415f`) | HEAD (F1a‴ + H′, `18ec81d`) |
|---|---|---|---|
| A1 ride low-kind episodes (one detector; onset / any) | 4 / 6 | **1 / 1** | 2 / 2 (6860, **new 5714**) |
| ride STOP frames / episodes / events (one detector) | 130 / 30 / 28 | 109 / 24 / 20 | 115 / 25 / 22 |
| A2 gate exit (seal baseline, no `--allow`) | 0 (545 leaves = seal gate) | **0**; ride 27/30 → 18/24, five empty 8/12 → 7/11 | not run |
| A3 doubleT_obstacle STOP frames | 193 | 193 (per frame identical) | not run (gate) |
| A4 set O (gate) | — | every object identical per frame | not run; node-path small_on_rail **not measured** |
| A5 rail-head box / 10 cm rail boxes first STOP | 44.86 m | 44.86 m (margins 0.01–0.04 all equal) | not run |
| A6 tests | baseline 1,969 | `8c88d5c`: 1,991 passed, 1 failed (`test_lidar_proxy_hook`, fails on `aec88d2` too: environment) | targeted files pass |
| A7 Falcon non-person STOP frames / person frames | 12 / 1,360 | **0** / 1,360 (first 124.84 m) | not run; expected 4 (S2 off; H′ keeps the 8 ceiling frames removed) |
| A8 switch-off identity | — | shown (see §1) | not re-shown |
| A9 X3 | base battery MEASURED (`probes/x3_base_aec88d2.json`) | candidate battery not run | not run |
| A10 CAUTION | ride 4,758 (one det.) | +13 ride, +12 Falcon (the removed STOPs) | ride 4,767 |
| A11 review | — | PASS WITH CONDITIONS, blocking B1 | — |
| am. 5 synthetic bags (N5 labels) | — | `8c88d5c` (F1a′+H′) vs off: identical on every frame of all 3 bags; P1's 12 background STOP frames unchanged; no dust STOP/CAUTION | — |
| am. 1/5 standing-train and dynamic probes | — | identical to base (S2 on) | — |

Amendments, one line each: **1** Falcon attribution (9.4 m STOP = the ceiling under a floor fit that climbed; 115 m =
static edge support) and designs H, S. **2** S measured 12→1; S2 (ground-plane spread) registered. **3** box rise above
the local rail line ≥ 0.034 m → margin ≤ 0.019 admissible, 0.01 added. **4** sweep (F1a 0.01–0.04, F1b, F1c) → F1a
0.01 + H + S2 selected. **5** organizer info of 19.10 → S2 must never delay/demote a moving or in-gauge object.
**6** review 1 → F1a′ (exclusion + advisory), H′ (above only), S2 withdrawn. **6b** near-bed path exempt; two
counterfactual tests run with F1a off. **7** F1a′ fails A1 (117/28/25, low 4/5) → cross-rail F1a″. **8** advisory mode
is what costs the effect → weak mode + cross-rail (F1a‴).

**Last finding (not in an amendment yet):** HEAD's new 5714 STOP is caused by the cross-rail rule: at 5709 (43.4 m,
centre, top 0.117, L 0.063 / R 0.173) and 5712 (45.6 m, left rail, top 0.066, L 0.117 / R 0.024) the rails' lines
disagree by > 0.04 m, the lower line is used, the clusters pass, and they build track 2098, which STOPs at 5714–5717
(F1a 0.01 without the rule rejected both; the weak flags differ only on those two frames;
`ride/amend6_8/`, scratch `ride/cand_18ec81d.jsonl`). 10484 is removed by HEAD although no F1 firing is on its own
track's hits (traced attribution): an association side effect, untraced.

## 3. Recommendation

**Do not merge F1a in any measured form yet.** The best result (F1a 0.01 weak) has review B1 (pieces of a long low
object along one rail raise their own reference); every B1 fix measured so far either loses the effect (exclusion,
advisory) or adds a false STOP (cross-rail 0.04). **H′ can ship on** after one confirming run (gate + Falcon on the final
commit): it removes the 8 Falcon ceiling STOPs, changes nothing on the gate, the ride, set O or the synthetic bags.
For a merge now: set `local_rail_margin` 0 (F1a off), keep H′ on, re-run gate + Falcon + switch-off identity. S2 stays
opt-in (Falcon 115 m: 4 frames remain; whether that support is inside the gauge is undetermined).

## 4. Open items

B1-safe F1a reference (e.g. the cross-rail rule only when the cluster's own rail is the higher one, or a minimum
number of independent rail crossings) — design, register, measure; trace 10484; F1 row 6860 (a 1.36 × 0.18 m line
0.23 m outside the right rail at the envelope edge) untouched by all variants; X3 candidate battery; node-path set O
`small_on_rail` (A4); review 2; ego-veto measurement (trace started: `scripts/` scratch `trace_egoveto.py`; E3 receding
probes STOP from 96–97 m in base and candidate, so the veto did not block them here — not yet explained).

## 5. Commands and data

Environment: `source <scratch>/f1/env.sh` = `PATH=/home/user/venv/rs/bin:$PATH RESENSE_REPO=/home/user/ReSense-f1
PYTHONPATH=/home/user/ReSense-f1:/home/user/ReSense-f1/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell
OMP_NUM_THREADS=1`; scratch = `/tmp/claude-0/-home-user-ReSense/314e4672-57bf-5bc8-aad1-a40ec29bc1c0/scratchpad/f1`
(raw runs: `ride/`, `falcon/`, `probes/`, `synth/`, `x3/`, `gates/`). Worktrees: `/home/user/ReSense-f1` (branch),
`/home/user/ReSense-base` (detached `aec88d2`, native built).

Data: `/data/cache/<six bags>`, `/data/cache/cloud_with_fake_obj`, `/data/cache/new_data` (ride, 221 splits, intake
manifest verified) — gate caches (zstd); `/data/decoded_f1/{roundT_squareT_pressureGate_squareT, cloud_with_fake_obj,
doubleT_obstacle, squareT_platform_squareT_switch}` (node-decoded, meta.json = P4 linux_intake hashes) + ICP in scratch
`probes/icp_*.json`; `/data/synth_f1` (empty spool; synthetic bags are streamed per bag); gate work dirs `/data/work_f1`.

```
# full gate (base worktree or branch), against the seal baseline
<scratch>/run_gate.sh <repo> <tag> 2 [--set k=v ...]          # = scripts/regression_gate.py --cache /data/cache --jobs 2 --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json
python docs/evidence/f1_false_alarms_2026-10-19/scripts/cmp_frames.py /data/work_f1/gate_base_aec88d2 /data/work_f1/gate_<tag>   # per-frame identity
# ride, one detector, with traces
python docs/evidence/f1_false_alarms_2026-10-19/scripts/replay.py --bag new_data --out <out> --lowref --tracks [--set lowobj.local_rail_margin=0 ...]
python docs/evidence/f1_false_alarms_2026-10-19/scripts/episodes.py <out>.jsonl --against <base>.jsonl --json <eps>.json
python docs/evidence/f1_false_alarms_2026-10-19/scripts/attribute_traced.py <base>.jsonl <out>.jsonl
# Falcon (streams 20 GB, ~6 min)
python docs/evidence/f1_false_alarms_2026-10-19/scripts/falcon_trace.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --out <out> [--set k=v] [--dump 4375-4405]
python <scratch>/score_falcon.py <scratch>/falcon/base.jsonl <out>.jsonl          # (copy: scripts/score_falcon.py)
# probes (judge's range_test, background A / standing train / dynamic)
<scratch>/run_measure_probes.sh <tag> "k=v;k=v"   <scratch>/run_s_probes.sh <tag> "k=v"   <scratch>/run_e_probes.sh <tag> <repo> measure|range
# synthetic bags (off vs candidate, per bag, streamed): scripts/synth_local.py --zst https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --bag <bag> --spool /data/synth_f1 --out <prefix>; scripts/synth_compare.py <prefix>
# X3: python scripts/robustness_battery.py --repo <repo> --cache /data/decoded_f1 --out <new.json> -j 2 [--reference <scratch>/x3/x3_base_aec88d2.json]
```
