# Set F dust battery: fixed clean placement

`scripts/dust_set_f.py` leaves the sealed `far_range_eval.py` unchanged. It uses
its six starts (46, 68, 98, 140, 168, 172), five kinds (person, box1.0, box0.5,
trolley, cable), a maximum of 110 consecutive source frames, 220 m start, bed placement,
lateral range ±0.6 m and original seed-0 object draws. Actual timestamps and
per-split speeds determine approach distance. No given-speed accumulation is
introduced. A missing frame or timestamp fails preparation.

All 110 source frames must be available, but the original Set F approach ends
when the target passes 8 m; the actual evaluated count can therefore be smaller.
The bank records both `requested_frames` and every evaluated frame. For example,
start 46 uses 102 frames and ends at 8.903 m. Each dust level uses exactly that
same frozen sequence, with no density-dependent truncation.

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

The corrected coordinate protocol was registered before fresh measurements in
commit `7e05aeb`; the immutable harness is `b9ad5f4`. Preparation additionally
freezes the clean detector's **actual applied** input-to-model rotation and its
rail height at 20 m, with source-payload and reference hashes. Attenuation and
new returns are generated in those same clean axes. Only new returns are inverse
mapped; retained source XYZ, intensity and ring values are restored exactly by
original indices. All densities use the identical reference. This is a flat
cloud height anchored at `rail_z(20 m)`, not a surveyed or graded rail plane.

The old partial preparation stopped after 15 banks and **before any evaluated
dusty level**. It used the pre-process legacy-placement model and did not record
the actual applied clean transform. The [interruption receipt](set_f_precoordinate_interruption.json)
preserves its provenance separately; no measured Set F coordinate error or dust
result is inferred from that unfinished attempt.

Per sequence and level the report includes first matched STOP/frame, every hit,
lost clean STOP frames, unmatched detections, false STOP frames and consecutive
false STOP episodes, CAUTION/FAULT/GO counts, and degraded frames. Matching keeps
the legacy fixed distance/lateral tolerance. A held detection matching the object
on a zero-clean-return frame is neither a supported hit nor a false detection.
These are deterministic simulation stresses, not calibrated physical dust data.

Prepare and evaluate from the immutable baseline:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  /home/resense/.venv/bin/python /home/resense/data/dust/harness_b9ad5f4/scripts/dust_set_f.py \
  --cache /home/resense/data/gate_cache/new_data \
  --bank /home/resense/data/dust/set_f_bank_pose_fixed \
  --out /home/resense/ReSense/docs/evidence/n3_dust_2026-10-18/set_f_baseline_pose_fixed \
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
The complete ride cache is verified; corrected measurements are running. No pass
is implied by successful harness tests. The complete-only
[verifier](summarize_set_f.py) checks all 30 sequences/four levels, exact source
cadence and the 8 m cutoff, recomputes every aggregate from captured rows, and
checks matching independently within the serialized geometry's 5 mm rounding
bounds. Boundary ambiguities remain explicit; a missing or partial sequence is
an error. Independent artificial-fixture tamper probes test the verifier's
bookkeeping and are separate from detector evidence.

The detached [corrected wrapper](run_set_f_corrected.py) requires the complete
`ride_receipt.json`, verifies the organizer archive SHA-256/size and all 221 × 51
frame counts, and independently validates cache stamps before starting the full
baseline battery. It keeps a process lock and records state in
`/home/resense/data/dust/set_f_corrected_status.json`; the current queue log is
`/home/resense/data/dust/set_f_corrected.log`. The evaluated source remains immutable
`baseline_9b92df5`, with one numeric-library thread and process priority 5.
