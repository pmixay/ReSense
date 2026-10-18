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
The full-gate proxy experiment remains excluded until complete.

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
