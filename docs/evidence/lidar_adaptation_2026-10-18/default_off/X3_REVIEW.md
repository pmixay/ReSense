# Selected-default X3: complete raw comparison

The complete battery on immutable `cecab1b` passes: **40 cases, 29,765 output rows,
260/260 metric checks**. The class and YAML defaults select zero orientation-replay
frames; no replay override was supplied. This is the user-selected opt-in policy.
The preceding default-four captures remain separate measured history and do not
establish global acceptance because they lost 13 existing Falcon STOP frames.

[Author revalidation](x3_independent_review.json) independently reloads both sets
of raw rows, checks their hashes/completion records, source/label/protocol identity,
input stamps and complete membership, rebuilds all metrics and the directional
PASS decision, then compares every serialized field after the documented latency
normalization. Every metric and every non-timing serialized field is identical.
There are zero lost or added STOP frames. The separate joint independent review
also verifies all 6,284 STOP frames and 204 STOP intervals, with no delayed
or shortened STOP.

[The execution receipt](x3_execution.json) preserves the exact command, wrapper,
producer status and logs. The run finished at **2026-10-18 11:29:56 UTC**, exit zero.
All 38 source-file hashes equal the selected runtime identity and remain unchanged;
the host native library is enabled and unchanged. Timing under concurrent work on
the shared one-CPU host is informational.

## Input scope

The **3,133 input matches are to the archived Linux 1.1 reference, not the missing
historical Windows Set O frame 332; that provenance gap remains open**.
[Reference preparation](../x3_reference_preparation.json) checks the current decoded
cache after changing only ZIP header conventions, requiring every whole-file hash
to match the Linux reference. Point arrays and compressed payloads are unchanged.
It does not prove equality to that unavailable Windows frame or equality between
the float X3 cache and the separately quantized ordinary-gate cache.

The ordinary default gate and complete Falcon comparisons have their own matched
controls and independent reviews. This X3 result supplies its measured part of the
joint acceptance decision; it does not establish universal detection performance.

## Durable evidence and reproduction

[The manifest](raw/x3_manifest.json) lists **167 members**, all decompressed and
hashed after packing, with the retained local originals rechecked. The archive is
`raw/x3.tar.gz` (2,132,519 bytes), SHA-256
`be17205f6fc720761a8e086e05d61125b6b5b676022a1e86ea21a9fb02080d9f`.
It contains every case's job, raw JSONL, completion record and process log, plus
unchanged report/review/execution receipts and the exact outer wrapper/status/logs.
No raw local evidence was removed.

After verifying `raw/X3_SHA256SUMS` from that directory, extract the archive to a
new folder. The original reference preparation must also have been reproduced:

```sh
mkdir -p /tmp/x3-selected-default
tar -xzf docs/evidence/lidar_adaptation_2026-10-18/default_off/raw/x3.tar.gz \
  -C /tmp/x3-selected-default
python docs/evidence/lidar_adaptation_2026-10-18/review_x3.py \
  --reference /home/resense/data/x3_reference/reference.json \
  --candidate /tmp/x3-selected-default/x3.json \
  --candidate-raw-root /tmp/x3-selected-default/x3 \
  --cache /home/resense/data/x3_reference/cache \
  --out /tmp/x3-selected-default/revalidated.json
```

Path relocation happens in memory; archived report/completion hashes and source
identities are not edited or waived.
