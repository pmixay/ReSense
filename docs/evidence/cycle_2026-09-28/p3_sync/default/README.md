# Combined P3/score defaults: full regression acceptance

Measured source: `b84ea8f229be8d11d9db82ebd337198803ce92bf`.
Baseline: the committed score-candidate gate for `ef1d8f5`.

- Full gate PASS: all 146 enforced rows unchanged; 208 comparable metrics unchanged.
- No waivers, missing rows or regressions. All six short recordings, all 11,271 ride frames, set O and 30 set F cases are present.
- Positive cached labels: rail 129/185 overall, 126/126 from frame 75; person 61/61.
- Empty ride: 130 STOP frames, 32 false events, 31 episodes. Five empty short bags: 40 frames, 11 events, 13 episodes.
- Separate per-frame monitoring comparison passes; negative alarm payloads and monitoring coverage are unchanged. Existing 16 set O GO overclaim flags remain.
- Continuation remains enabled at 0.3 seconds. P3 onset/cross-ring/bed flags remain disabled by default; this run does not accept enabled variants.

Backend: native, package-local binary SHA-256 `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534`.
Run: four jobs in `resense-cycle-dev`, PYTHONPATH points to the measured checkout, OMP/OPENBLAS/MKL thread counts each 1. Runtime timing under shared load is diagnostic only.

The earlier incomplete NumPy run was aborted when the backend mismatch was found; its record is retained in `aborted_numpy_attempt.json`. It is not acceptance evidence.
The previous score-source seal is retained before its replacement by this measured-source seal.
Captures and synthetic output are losslessly compressed; hashes cover the archived bytes.
