# N3 dust fix — registered acceptance protocol (19.10.2026)

Registered **before** any acceptance measurement of the candidate below. Owner: P3 lane (agent),
ordered by P1. Base: `main` `aec88d2` (1.2.0 candidate, 38 sealed files, digest `68dee667…`).
Branch `det/n3-dust-robustness`. All results are **synthetic-model results**: no physical dust
recording exists; the generator (`resense/dust.py`, harness `b9ad5f4` semantics, unchanged) is a
deterministic volumetric-return and ray-attenuation stress, not measured dust physics.

## Candidate (frozen at the registration commit)

Switch: `dust.enabled` (new config block `dust:` in `configs/default.yaml` and the ROS copy,
`DustGuardConfig` in `resense/config.py`), **off by default**. Code: `resense/dust_guard.py`, three
hooks in `resense/detector.py` (`_fit_track`, `_dust_qualify` after the low stage, health
post-processing). Off: no guard object exists and no code path changes.

On, per frame:

1. **Assessment.** Returns inside the empty gauge interior (X 5–60 m, |dy| ≤ 1 m, 0.3–2.7 m above
   the rail head) with no other distinct return within `r(R) = 0.10 m + 0.004·R` are *isolated*.
   Active when isolated density ≥ 0.3 /m³ **and** isolated returns occupy ≥ 35 % of the interior
   cells (5 × 0.5 × 0.6 m); hysteresis: off after 10 frames below 0.15 /m³ or 20 %. A Poisson
   correction gives the field density used below. No intensity threshold anywhere.
2. **While active:** (a) health `warn` (CAUTION; `error` is never lowered), message names diffuse
   volumetric returns (dust / suspension), `monitored_range = clear_distance = 0`;
   (b) obstacle candidates (corridor, low, straddle, near-bed) keep only returns with at least
   `k(R)` neighbours within `r(R)`: the smallest `k ≥ 3` that a diffuse field of the measured
   density reaches by chance with probability ≤ 0.001 (beyond the measured 60 m: `k = 3`).
   No frame point is deleted from the cloud; unsupported returns cannot feed a STOP;
   (c) `track_filter`: unsupported returns near the track (|dy| ≤ 3 m, X < 70 m) are withheld
   from the track-model fit only.
3. **Light mode** (track filter only, no health change, no candidate filtering): a 20-frame mean
   isolated density ≥ 0.05 /m³ and mean spread ≥ 0.08.

## Development record (not acceptance)

Development used **dev seed 7** only (`--seed 7`) on the five empty recordings and
`doubleT_obstacle`, plus diagnostics of the *unchanged baseline* on the registered seed
(`diag/`: support statistics, ablations, oracle-track test). The registered seed 20261018 was
not used to tune any candidate parameter. Dev results are kept in `dev/`. Diagnostic findings
that shaped the candidate: (i) medium/high false STOPs are unsupported generated returns, while
a real object's returns are ≥ 95 % supported; (ii) a real person merges with dust into an
oversize blob and is lost; (iii) the far-field / platform false STOPs that remain are **real
structures** whose zone flips because the dust (injection and attenuation alike) perturbs the
track model — with the clean track model (oracle) they disappear; (iv) a non-dust control (2 %
uniform random point drop) also raises squareT_platform_squareT_switch from 3 to 7 STOP episodes:
part of the low-density failure is pre-existing sensitivity of the track model.

## Acceptance (unchanged from the task / N3 registration; seed 20261018; densities as registered)

Runs: `scripts/dust_battery.py --seed 20261018 --set dust.enabled=true` on the five empty
recordings, `doubleT_obstacle` and Set O, clean/low/medium/high; the same with the switch off
as the paired control on the same source; `--dim-labels 1` dimmed-object control (on and off).

| # | Criterion | Pass rule |
|---|---|---|
| 1 | Empty recordings | each of 5 × {low, medium, high}: STOP episodes ≤ its own clean + 1 (15 cells) |
| 2 | Low density | person first inside STOP ≥ 90 % of clean distance and all clean inside person STOP rows kept; rail object: all clean inside STOP rows kept (any loss reported, counts as FAIL) |
| 3 | Medium / high | no silent GO: every frame of every recording at medium/high either STOP or degraded (decision_level warn/error) with a dust/visibility message and clear range 0 while degraded by the guard; retained positives reported |
| 4 | Clean unchanged | full regression gate (`--baseline regression_baseline_2026-09-29_shell_off.json`, ride and Set F) exit 0 without `--allow`, switch **on**; X3 battery PASS against a fresh `aec88d2` X3 reference, switch on; dimmed real obstacle (`--dim-labels 1`) clean and low: all STOP rows of the switch-off run kept |
| 5 | Falcon | full 4,443-frame recording, switch on: all 1,372 STOP frames and 8 STOP intervals of the committed run kept; windows 0–1,700 (empty) and 2,700–4,400 (person) with the generator extended to the Falcon (no ring, field-of-view clip, ROS axes through the node's own mapping/calibration): criteria 1 and 3 on the empty window, person STOP retention reported per level |
| 6 | Honesty | every result labelled synthetic; failures reported with numbers |

Switch-off parity (required regardless): with `dust.enabled=false` every non-timing output equals
`aec88d2` — shown on the full gate rows (frame-level comparison against a fresh `aec88d2` gate),
X3 raw rows, and the dust battery clean/low/medium/high rows of both sources.

Instrumentation rule: the diagnostic scripts (`diag/`) are never used as acceptance numbers;
acceptance numbers come from the unmodified battery / gate / X3 / stream outputs and are
re-derived from raw rows by an independent script.

Decision: the candidate may be recommended **on by default** only if all of 1–5 pass. If any
fails, it is reported as FAIL with the cause, and the recommendation is off-by-default or do not
ship. Independent review by a fresh agent that did not write the change is required before the
report's recommendation.
