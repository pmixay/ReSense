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

## Corrected full gate and fresh control

`gate_control_and_7b.tar.gz` retains both completed ordinary-gate captures:
the immutable `9b92df5` control and corrected `7b7b02c` candidate, with the same
native library, cache, original receive stamps and eight ride chunks. Each arm
contains 15,269 ordinary rows and 3,060 Set F scoring/placement rows, plus its
configuration. Unchanged gate reports, producer receipts and the independent
comparison are included. The earlier partial NumPy control is excluded.

The independent comparison reconstructs every summary from these rows. All 208
non-latency metrics and all common non-timing ordinary fields are identical;
the only ordinary additions are explicit orientation-readiness fields. No STOP
or detection payload is lost or added. All Set F scoring/placement rows are
identical. Set F omits complete detection lists, so its stored hit/false-positive
assignments cannot be independently rebuilt from this archive; aggregate counts,
source membership, stamps, placements and every stored row were checked.

Extract `gate_control_and_7b.tar.gz` into the same scratch directory. With the
two source commits available as separate immutable checkouts, review it using:

```sh
python docs/evidence/lidar_adaptation_2026-10-18/review_gate_frames.py \
  --reference /tmp/lidar-evidence-review/control/gate.json \
  --candidate /tmp/lidar-evidence-review/candidate/gate.json \
  --reference-work /tmp/lidar-evidence-review/control_work \
  --candidate-work /tmp/lidar-evidence-review/candidate_work \
  --reference-source /path/to/9b92df5 \
  --candidate-source /path/to/7b7b02c \
  --cache /path/to/verified/gate_cache \
  --out /tmp/lidar-evidence-review/gate_review.json
```

This full gate does not substitute for the separately required final-corrected
X3 stress capture. All batch timings are informational under shared CPU load.
