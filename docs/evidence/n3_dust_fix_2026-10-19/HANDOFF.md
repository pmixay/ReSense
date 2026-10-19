# N3 dust fix — hand-off (19.10.2026, ~16:10 UTC)

Stopped on the coordinator's (P1) order. **No independent review, no gate/X3, no REPORT.md yet.**
All numbers are synthetic-model results (generator `resense/dust.py`); no physical dust recording exists.

## State of the dust guard
- Code: `resense/dust_guard.py` (new), hooks in `resense/detector.py` (`_fit_track` track filter,
  `_dust_qualify` after the low stage, health post-processing), `DustGuardConfig` in `resense/config.py`,
  `dust:` block in `configs/default.yaml` and the synced ROS copy. Tests: `tests/test_dust_guard.py` (31 pass).
- Switches / defaults: `dust.enabled: false` (master); `track_filter: true`; `light_spread: 0` (light mode off,
  it lost real STOPs at low in dev); `attach_factor: 0`. Design and frozen parameters: `PROTOCOL.md`
  (registered at `1de9c47` before any acceptance run).
- Off = `aec88d2`? With `enabled: false` no guard object exists and no code path changes (by construction).
  **Measured only on the Falcon full recording** (switch off and on both equal the committed run, below).
  The paired battery/gate/X3 parity runs against the `aec88d2` worktree were **not run** (stopped).
- Guard never activates on the clean data examined: six original bags (signal max 0.13 /m³, spread ≤ 0.04
  vs thresholds 0.3 / 0.35, `diag/signal_stats.py`) and all 4,443 Falcon frames.
- Guard does **not** use temporal/static persistence (organizers' point 3b is respected); it uses local
  spatial support only, no intensity threshold.
- Timing: under medium/high dust p95 0.45–0.72 s/frame on this shared 4-core host (track filter dominates).

## Acceptance results that exist (registered seed 20261018, switch on; raw in `raw/battery-on/`,
independent re-derivation `acceptance_summary.py` → `acceptance_battery_on.json`, 0 disagreements with the
battery counters; table `battery_on_table.txt`)
| Criterion | Result |
|---|---|
| 1 empty, ≤ clean+1 | **6/15 PASS.** Episodes clean→low/med/high: platform 0→1/6/3, roundT_doubleT 0→0/2/5, pressureGate 1→1/7/9, roundT_squareT 0→0/5/12, switch 3→12/2/0 (baseline medium 25/25/22/58/71). FAIL |
| 2 low | person 61/61 inside rows, first 55.51→55.51 m PASS; rail object 104/128 rows (guard inactive at low = baseline behaviour) FAIL |
| 3 no silent GO | 14/14 PASS (all medium/high frames degraded with the dust message and clear range 0; 0 GO). Real obstacle medium: person 61/61, object 129/185; high: person 57/61, object 0 |
| 4 clean / gate / X3 / dark | **not run** |
| 5 Falcon | full recording, switch off and on: 1,372 STOP frames, 8 intervals, 0 decision differences vs `falcon_full_v110.jsonl`; on vs off identical in every non-timing field (`falcon_full.json`, raw `raw/falcon-full/`). Dust windows **not run** (harness `falcon_dust_stream.py` smoke-tested on 25 frames) |
Set O (switch on): medium 8→11 episodes, high 27; per-object losses in `battery_on_table.txt`.

## Dev results vs the registered rows
`PROTOCOL.md` table (dev seed 7, `dev/g5_table.txt` = frozen candidate, `dev/g6_table.txt` = track filter off).
The acceptance seed reproduces the same picture. Prototype `dev/b1_boundary_check/` (cluster continuous with a
boundary → advisory) gave outputs identical to g5 on 6 bags × medium/high: the rule never fired; not pursued.

## Diagnosed causes of the remaining failures (`diag/`)
- Low (guard inactive): far real structures at the gauge edge flip into the gauge because the cloud perturbs the
  track model; with the clean track model (oracle) switch low = 4 episodes (pass); a non-dust 2 % uniform point
  drop already gives 3→7. Pre-existing track-model sensitivity (`resense/track.py`, other lane).
- Medium/high: remaining STOPs are real wall-side structures; dust attenuates the far walls, the wall-derived
  curvature drops (e.g. 0.8e-3 vs 2.2e-3 /m) and the axis shifts 0.5–2 m at 40–60 m.

## How to run the acceptance (`run_acceptance.py`)
```
python docs/evidence/n3_dust_fix_2026-10-19/run_acceptance.py --stage <stage> \
  --source <candidate checkout> --reference <aec88d2 worktree, native built> --on-source <candidate worktree with dust.enabled: true>
```
Stages: `battery-on|off|ref`, `dim-on|off|ref`, `gate-ref|off|on`, `x3-ref|off|on` (x3-ref first),
`falcon-full`, `falcon-empty-on|off`, `falcon-person-on|off`. Raw to `/data/acceptance/<stage>`, receipts and
logs to this folder; it refuses to overwrite. Needs: node-decoded caches `/data/decoded/<bag>` (six bags +
`cloud_with_fake_obj`; `docs/evidence/judgement_2026-10-13/scripts/cache_decoded.py <bag> <out>`), gate caches
`/data/gate_cache` (six bags, Set O, ride `new_data`: `scripts/cache_frames.py --every 1 --int16 --stamps`,
ride per VM_GUIDE §2.3), Falcon streamed from https://disk.yandex.ru/d/SfBeRHbs8bNJAQ (nothing stored).
Env: `OPENBLAS_CORETYPE=Haswell`, one thread; load only `resense/_resense_native.so` (sha 67fa0887…) — a stray
`_resense_native.cpython-312*.so` from `pip install -e` is loaded first if present (dev runs g1–g4 used one).
Then `acceptance_summary.py --on/--off/--ref ... --labels labels`, `compare_rows.py` for parity,
`falcon_compare.py` for Falcon.

## Organizers' dust non-regression set (P1, 19.10; not yet run)
Synthetic bags (new_synth_data): dust bursts at frames platform 21, 27, 35–36; switch 481, 483, 611, 613;
tunnels 70, 166–167, 195, 446 (markers: branch claude/optimistic-mccarthy-z5nmwd @3501a72,
docs/evidence/synth_markers_2026-10-19/). Sealed 1.1.0 gives no STOP/CAUTION from the dust there; any guard
candidate must also give none, and every listed object must still STOP inside the gauge. A protocol amendment
must be registered before measuring it. Expected: these bursts (1–14 points, 1–2 frames, 3.4–7.2 m) are far
below the guard's activation (≥ 0.3 isolated returns/m³ over ≥ 35 % of the 5–60 m interior) — unverified.

## Open items
1. Parity off == aec88d2 on battery, gate rows and X3 (stages battery-off/ref, gate-off/ref, x3-ref/off).
2. Gate and X3 with the switch on; dimmed-object control (dim-on/off/ref).
3. Falcon dust windows; organizers' synthetic dust non-regression; Set F dust (not planned in the protocol).
4. Independent review (fresh agent), REPORT.md.
5. Recommendation at this point: **do not enable by default** — criteria 1 and 2 fail; possible off-by-default
   ship only after item 1 and 2 are shown.
