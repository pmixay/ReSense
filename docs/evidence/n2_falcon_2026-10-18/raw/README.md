# Completed N2 raw measurements

`raw_completed.tar.gz` contains the completed JSONL measurements referenced by
the N2 reports. Plain JSONL files are ignored by the repository. Their local
originals remain in place; this archive makes the evidence portable without
changing the scripts' paths.

[manifest.json](manifest.json) lists every member's relative path, byte count and
SHA-256, together with the archive hash. Every member was decompressed and hashed
after packing, and every local original was rechecked. No active `proxy/` or
`orientation_obstacle/` output is included. Those experiments require separate
archives after they finish.

Restore from the repository root:

```sh
cd docs/evidence/n2_falcon_2026-10-18/raw
sha256sum -c SHA256SUMS
tar -xzf raw_completed.tar.gz -C ..
```

Members restore directly beneath the N2 evidence folder, including full Falcon,
field variants, required eight-orientation captures, ride split 200, static
attribution and per-frame characterization. The interrupted Falcon attempt is
retained under `falcon_interrupted_1300/` as explicitly incomplete diagnostic
history; it is never combined with the complete rerun or treated as acceptance.
Summaries, scripts, source receipts and independent raw-cloud annotations remain
ordinary committed files outside this archive.

The later `raw_orientation24.tar.gz` contains all 25 completed baseline/control
captures for the expanded automatic-orientation experiment. Its separate
[manifest](orientation24_manifest.json) verifies all member hashes, and
`ORIENTATION24_SHA256SUMS` verifies the archive. Restore it from this folder with
`tar -xzf raw_orientation24.tar.gz -C ..` after checking its checksum. Its known
wrong-orientation cases are retained; completion does not imply acceptance.
The now-completed full-gate proxy experiment has its own archive below.

`raw_orientation_bound_fix.tar.gz` separately preserves all nine completed
corrected-source `7b7b02c` captures (control plus eight supported mappings).
[Its manifest](orientation_bound_fix_manifest.json) verifies every member and
`ORIENTATION_BOUND_FIX_SHA256SUMS` verifies the archive. Restore it with
`tar -xzf raw_orientation_bound_fix.tar.gz -C ..`. The earlier captures remain
unchanged, with their original source identity.

`raw_proxy_decoded.tar.gz` contains the 20 completed paired captures for all ten
decoded recordings (5,665 frames per arm). [Its manifest](proxy_decoded_manifest.json)
and `PROXY_DECODED_SHA256SUMS` verify every member and archive; restore with
`tar -xzf raw_proxy_decoded.tar.gz -C ..`. These stress-test records include
the measured regressions. The separate full-gate hook output is not included.

The archives contain detector/measurement records, not the large raw point-cloud
datasets. Those retain their separate organizer-source, cache and cleanup receipts.


`raw_full_proxy.tar.gz` preserves the completed full transformed-input gate:
15,269 ordinary serialized rows, all 3,060 Set F scoring rows, 18,329 per-input
transform receipts, retained hook/helper copies and activation records, full
source/coverage receipt, gate outputs/logs, and same-runtime revalidation.
[Its manifest](full_proxy_manifest.json) verifies all 32 members and retained local
originals; `FULL_PROXY_SHA256SUMS` verifies the archive. Restore with:

```sh
sha256sum -c FULL_PROXY_SHA256SUMS
tar -xzf raw_full_proxy.tar.gz -C ..
```

This experiment finished with 36 gated regressions and is explicitly **not**
default detector acceptance. Its source is immutable `9b92df5`; the external
hook changes every input, including Set F after injection. The report's Git
stamp identifies the harness checkout, while the receipt and activation records
identify the actual loaded detector source. Full point payloads are not stored
in this output archive; source data/cache receipts and the retained transform
code preserve the reproduction contract. Set F scoring rows do not contain all
detections, so raw hit assignment cannot be independently reconstructed.

The paired untransformed same-runtime control is preserved separately in
`../../lidar_adaptation_2026-10-18/raw/gate_control_and_7b.tar.gz`. After restoring
that archive and making the original source/cache locations available, reproduce
the comparison from the repository root:

```sh
python docs/evidence/n2_falcon_2026-10-18/summarize_full_proxy.py \
  --control docs/evidence/lidar_adaptation_2026-10-18/control_9b_native \
  --proxy docs/evidence/n2_falcon_2026-10-18/full_proxy_gate_verified \
  --control-source /home/resense/data/control_lidar_9b92df5 \
  --proxy-source /home/resense/data/n2/baseline_9b92df5 \
  --cache /home/resense/data/gate_cache \
  --out /tmp/full_proxy_same_runtime_summary.json
```

Use the control archive's manifest paths when restoring its `control_work/`
into the expected `control_9b_native/work/` location. The evaluation label and
speed metadata must match the original `9b92df5` hashes; the verifier checks
those separately from the detector-only source export.
