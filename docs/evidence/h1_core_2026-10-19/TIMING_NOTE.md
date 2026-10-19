# Isolated timing follow-up (console transcript)

These are transcribed outputs of the existing
`tests/test_algorithm.py::test_timing_with_accumulation`, not reconstructed
per-frame telemetry. The JUnit files establish the test outcomes; the individual
19 latency samples were not saved. No formal speed comparison is claimed.

Both commands used the same Python/Haswell/one-thread/library environment as the
other runs, `RESENSE_REQUIRE_SYNTHETIC=1`, and ran **sequentially**, after the full
suite's timing failure:

```text
base 9621024, /tmp/opencode/h1-core-reference:
[synthetic, this machine] detector with accumulation:
mean 13.9 ms, p95 17.7 ms, max 18.3 ms over 19 frames
1 passed in 2.21s

candidate fd89712, /home/aiops/resense:
[synthetic, this machine] detector with accumulation:
mean 18.8 ms, p95 27.4 ms, max 103.9 ms over 19 frames
1 passed in 2.65s
```

The full-suite candidate failure (p95=153.68695145007223 ms against150 ms) stays
in `full-tests-c.xml`. Passing these separate isolated runs does not prove the
full-run outlier was caused solely by other machine load.
