# Full Falcon: selected default retains prior STOP behavior

The selected `cecab1b696b8c2e101207601acd8faed96c8bfb8` source, with startup replay disabled by default, passes the complete 4,443-frame comparison against an immutable `9b92df56e802d9d63f83f2fc5e5b07374db669c7` control using the same harness, Haswell BLAS dispatch, one thread and native binary. Neither run overrides detector configuration. [The independent review](independent_review.json) verifies recorded stamps, source identities, complete coverage and exact shared non-timing serialized fields.

Both captures produce 1 FAULT, 8 GO, 3,062 CAUTION and 1,372 STOP frames. All eight STOP intervals are identical, with no added, lost, delayed or shortened STOP. This retains all 13 STOP frames lost by the rejected default-replay4 candidate, including person-associated frames 2972–2975. The expected differences are the new orientation-confirmed diagnostic and the explicit unconfirmed message on the initial frame, which was already FAULT with zero range.

An initial comparison against the older full-Falcon capture failed exact coefficient equality: maximum differences were 1.36e-17 in curvature, 5.03e-16 in yaw and 1.78e-15 in floor coefficients; operational fields and STOP intervals were already identical. That [failed result](historical_baseline_review.json), its exact [review source](historical_review_source.py) and [quantification](historical_numeric_differences.json) remain preserved. The historical run did not record BLAS dispatch. Runtime dispatch is a plausible explanation; the fresh matched-runtime control establishes exact equality without assigning a numerical tolerance or rewriting the historical result.

Both completed captures, wrappers, source receipts, logs, summaries and reviews are retained in [the verified archive](../raw/falcon_default_off.tar.gz), with the [member manifest](../falcon_default_off_manifest.json). Plain local captures remain available. The wrappers take about eleven minutes each under concurrent load on the exposed one-CPU host; these durations establish no throughput claim.

To repeat the read-only comparison after restoring the archived files to their recorded repository locations:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  /home/resense/.venv/bin/python \
  docs/evidence/n2_falcon_2026-10-18/review_falcon_default_off.py \
  --reference docs/evidence/n2_falcon_2026-10-18/falcon_default_off_control
```

The verifier also requires the recorded immutable source checkouts and decoded cache metadata. This is serialized behavior preservation, not surveyed obstacle or gauge ground truth. Existing static-support and person-detection limitations remain. Replay4 remains explicit opt-in with its known losses; its earlier-detection gains are not claimed for the selected default. Full original gate and X3 acceptance are checked separately before resealing.
