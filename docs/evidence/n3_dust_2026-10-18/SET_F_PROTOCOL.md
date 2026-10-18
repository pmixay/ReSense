# Set F dust battery: fixed clean placement

`scripts/dust_set_f.py` leaves the sealed `far_range_eval.py` unchanged. It uses
its six starts (46, 68, 98, 140, 168, 172), five kinds (person, box1.0, box0.5,
trolley, cable), 110 consecutive source frames, 220 m start, bed placement,
lateral range ±0.6 m and original seed-0 object draws. Actual timestamps and
per-split speeds determine approach distance. No given-speed accumulation is
introduced. A missing frame or timestamp fails preparation.

A separate immutable **baseline** detector advances clean legacy placement.
Before any evaluated dusty detector runs, the bank freezes each object's full
precision specification, placement model, render seed, clean return count,
source hash and injected-cloud hash. Re-rendering must match the exact hash at
every level. This preserves the legacy model-derived placement without allowing
the evaluated detector or the dusty cloud to move the object. It is not surveyed
truth. The bank stores geometry instead of duplicating gigabytes of backgrounds.

Dust uses the registered `dust.py` clean/low/medium/high presets and seed
**20261018**. Dust is applied after the same clean injection. The clean physical
object remains in the scoring denominator when attenuation removes its returns;
observed-return hits are also reported separately. The detector receives neither
the bank nor the injector's `obstacles` metadata. No suppression candidate is
integrated into this harness.

Per sequence and level the report includes first matched STOP/frame, every hit,
lost clean STOP frames, unmatched detections, false STOP frames and consecutive
false STOP episodes, CAUTION/FAULT/GO counts, and degraded frames. Matching keeps
the legacy fixed distance/lateral tolerance. A held detection matching the object
on a zero-clean-return frame is neither a supported hit nor a false detection.
These are deterministic simulation stresses, not calibrated physical dust data.

Prepare and evaluate from the immutable baseline:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python scripts/dust_set_f.py \
  --cache /home/resense/data/gate_cache/new_data \
  --bank /home/resense/data/dust/set_f_bank \
  --out docs/evidence/n3_dust_2026-10-18/set_f_baseline \
  --placement-root /home/resense/data/n2/baseline_9b92df5 \
  --detector-root /home/resense/data/n2/baseline_9b92df5
```

`--mode prepare` and `--mode evaluate` separate the stages. Preparation and
measurements resume only after matching source, configuration, script, bank and
output hashes. All 30 sequences must exist before evaluation. A new detector
candidate may consume the same bank only if every clean rendering still matches;
changing an injector or sensor mapping cannot silently change the test.

Focused tests cover the original random schedule, timestamp/near-pass bounds,
removal of oracle metadata, per-frame loss/episode accounting, and a real Open3D
full-precision bank round trip with intentional rendering-drift rejection.
Production measurements await the complete ride cache; no pass is implied by
successful harness tests.
