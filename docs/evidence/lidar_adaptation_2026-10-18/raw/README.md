# Raw integration evidence

The archives retain the original serialized bytes. Plain local working files are
kept for review; the archives avoid committing generated JSONL trees. Each
manifest records every member's size/SHA-256, the archive hash, the measured
verification time and the retained original path. `archive_verified.py` reads
back every compressed member and rechecks that every original stayed unchanged.

`x3_preboundary.tar.gz` contains the completed **f5ff15f** X3 run: 40 cases,
29,765 rows, worker completion records/jobs/logs and its unchanged report.
Its 161 members were verified on 18 October. This run precedes the replay-memory
correction and is **not final 7b7b02c acceptance evidence**. The independent
review found all metrics and all non-timing serialized fields identical to the
original 1.1.0 reference, including every STOP frame.

Verify and extract without modifying the repository:

```sh
cd docs/evidence/lidar_adaptation_2026-10-18/raw
sha256sum -c SHA256SUMS
mkdir -p /tmp/lidar-evidence-review
tar -xzf x3_preboundary.tar.gz -C /tmp/lidar-evidence-review
```

From the repository root, reproduce the old-run review using the already
verified historical reference/cache, or their relocated equivalents:

```sh
python docs/evidence/lidar_adaptation_2026-10-18/review_x3.py \
  --reference /home/resense/data/x3_reference/reference.json \
  --candidate /tmp/lidar-evidence-review/x3_preboundary/report.json \
  --candidate-raw-root /tmp/lidar-evidence-review/x3_preboundary \
  --cache /home/resense/data/x3_reference/cache \
  --out /tmp/lidar-evidence-review/x3_preboundary_review.json
```

The raw-root option changes only in-memory file locations; raw hashes, worker
identity, source inventory, labels, protocol, row coverage and reconstructed
comparison results still have to match. `prepare_x3_reference.py` documents
recreating the reference/cache from the decoded originals: all 3,133 resulting
NPZ files must match the historical whole-file hashes. No live decoded cache is
rewritten. The original 1.1.0 raw archive remains under
`docs/evidence/p4_eval_1.1.0_2026-10-16/raw/`.
