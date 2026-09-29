# Low-ray support full gate — rejected candidate

The candidate in this archive **did not pass** and was not integrated into the detector branch. The wrapper confirmed stable source, configuration and native identities; the regression gate returned exit code **1** after 685.5 seconds.

## Gate result

The candidate was evaluated with default configuration and no metric allowances against the accepted complete-timing baseline (`bc75abe`, baseline file SHA-256 `357852e788471faf270e4c31f070e39e01123e0645e396ada512496c67df969e`). There was **one gated regression**: ride STOP episodes rose **31 → 32**. Ride STOP frames stayed at 130 and alarm events at 32. The other 207 gated metrics matched; none improved. Six Set F approaches across five kinds matched all **3060 per-frame rows exactly**. Five-empty and Set O aggregate metrics also matched.

A semantic comparison, excluding only runtime-latency fields, found **585 changed rows** in the recorded captures: `21` in ride chunk 1, `15` in chunk 4, `1` in chunk 5, `143` in chunk 7, and `405` in the square-T platform recording. **53 rows changed their detections** and **533 changed their warning text**. The row-level details are in [`comparison.json`](comparison.json).

On the empty ride, four baseline STOP frames disappeared and four new STOP frames appeared. The new low-return logic also shifted reported low-object distance by **9.26 m** at `new_data_205_0030` (49.74 → 59.00 m) and **11.78 m** at `new_data_205_0031` (47.59 → 59.37 m). It added ordinary STOP detections at frames 0033–0034 and low STOP detections at 0046–0047. This is a measured behavior change with no Set F gain and one extra ride STOP episode.

## Candidate and data identity

- Candidate commit: `1e2a3ffe9307e1aba4d5a61304a34c58a3874f12`; detector source digest: `f7e38ec6db7043d66d03b42b4440adc106b634235e7199b915421be627cef584`.
- Effective default config digest: `22a30ff265035e06358a21696cfb8bc61b598d16e5a64aa3536abfefbc4bd5fb`; native library SHA-256: `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534`.
- Registered protocol SHA-256: `fb6fd0e044996f5c3b0d331e1fc5cc0e3c09d6c8c6c8e0f86ffbd68b853176ae`; exact candidate source diff: `candidate-source.patch`.
- The run used all 11,271 ride frames, all six organizer recordings, Set O and 30 Set F sequences. See [`cache_identity.json`](cache_identity.json) and `cache/new_data_intake_manifest.json` for input provenance.
- The exploratory synthetic 50 m screen (0/16 → 12/16) motivated the candidate but is not holdout evidence. Full-gate Set F rows were unchanged.

`gate.json`, `gate.txt`, identities, candidate outputs and compressed per-frame captures are retained here. Timing rows are informational because the run was measured alongside other work; no speed gain is claimed.
