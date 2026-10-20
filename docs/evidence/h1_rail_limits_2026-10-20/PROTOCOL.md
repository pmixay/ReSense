# H1 rail limits — preregistered protocol (2026-10-20)

Scope: `/home/aiops/resense`, HEAD `f56ad5e62d9d051811c804734c7731b6951eae90`.
Evidence only; no detector/configuration/index/branch changes. No G3. Write only
this evidence directory and `/tmp/opencode/h1-rail-limits` on the VM. Each file <20 MB.

## Questions and acceptance, fixed before experiments

1. Can the unmodified rail estimator actually select a non-host pair? The host
   pair is **declared by scene geometry**, center 0 m, heads at +/-0.795 m.
   Distractors have center +/-0.4, +/-0.6 or +/-1.59 m; head heights/widths may
   differ. Search results, including unsuccessful attempts, will be retained.
   A selected wrong pair requires actual `estimate_rails` score >=0.05,
   >=2 slabs, captured `center`, `xm`, `mids`, and midpoints nearer the declared
   distractor than the host (tolerance 0.12 m). Mixed/inconsistent fits are
   separate; an injected coordinate error alone does not count.
2. Does wrong selection produce false collision core/STOP or miss? Target
   column width 0.46 m, height 3.22 or 4.12 m, distances 17/37/67 m.
   Independent analytic host envelope: |Y|<=1.05 m, height 0.12..3.0 m above
   **host** head Z=-1.83. Entire outside target has |lateral|-0.23>1.05;
   inside target intersects that envelope with observed returns. Check both
   geometry and raw target points. A reproducible false core or STOP is a
   finding, not something to tune away. Failure to force real wrong selection
   is UNVERIFIED, not PASS. Existing 72 ambiguous-pair cases are not evidence
   of wrong selection and are not reused as such.
3. No rails: cast a real bed/walls/target scene with **no rail boxes**, with
   unchanged bed and, separately, fixture's higher rail-free floor. Process
   14 complete scans from a fresh detector; retain all scan outputs. No fresh
   collision core is expected without a current paired-rail anchor. STOP from
   other rules, warning and clear range are recorded rather than conflated.
4. Rail loss: first obtain confirmed inside core/STOP with actual rails, then
   remove rail boxes for 14 scans with target present, and separately remove
   the target as well to measure bounded tracker retention. Test actual
   floor-shadow/held state if physically achievable; a supplied held model is
   separately labelled component-only. Retained tracker evidence is not a
   new core. Never claim an observed bound beyond the tested 14 scans.

## Controls and verification

* For each negative, same caster/estimator/matcher must find correct host rails
  and an inside core/confirmed detection on a paired control. Include outside
  correct-pair control. Preserve source hash and exact raw XYZ/ring/label hashes.
* Independently implemented nearest-ray/AABB caster, first validated against
  known `h1_physical.py` exact arrays/hashes and known case45 target count 84.
  Rail heights remain within estimator's plausible 0.08..0.5 m above bed;
  stronger distractors 0.4..0.48 m are synthetic raised rail-like ridges, not
  a prevalence claim for real track. All returns are nearest visible surfaces.
* Full pipeline: default `DetectorConfig`, fresh `Detector`, observed raw
  points only. No supplied track, coordinate shift or fitted-oracle model.
  Component supplied-coordinate tests are named and reported separately.
* If tracing is used, compare every non-timing `FrameResult` field, arrays
  byte-for-byte, plus full tracker state, with a plain run of the same input.
  Set previous latency to 42 ms identically in both arms (None on first scan)
  to prevent wall-clock feedback into health; this is not a latency benchmark.
  Trace actual estimator returns, anchor/interval returns and core branches.
* Re-derive pair midpoint agreement from raw rail-labelled returns, and core
  erosion from captured dy/h/interval using independent scalar envelope math.
  Audit every final row, not just counts. Positive controls for zero findings
  and deliberately perturbed checks for comparator/matcher sensitivity.
* Save compact JSON all 14-scan outputs, raw examples and snapshots; raw NPZ
  for reproducible inputs. Inspect a few raw rows/plots. Record failures and
  corrections, and any unverified mechanism.

Runtime: `/tmp/opencode/resense-b4-venv/bin/python`; libraries
`/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu`;
`RESENSE_REPO=PYTHONPATH=/home/aiops/resense`, `OPENBLAS_CORETYPE=Haswell`,
`OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=1`, `PYTHONDONTWRITEBYTECODE=1`.

Exploratory forcing and final directed replays will be clearly distinguished.
This establishes conditional synthetic limits, not a release gate or H1 closure.
