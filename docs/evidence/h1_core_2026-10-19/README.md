# P3 H1: positive collision evidence — 19 October 2026

**Bounded author checks pass on `fd897124612c42fd60a47327a4b6f97490ac8d2f`.**
The reproduced standing H4 case45 at67 m is fixed. **H1 overall / inherited High
remains OPEN:** long-range misses and common-mode axis-error failures remain.
Independent P4 review and P1 selection/reseal are pending.

Development branch `det/h1-positive-core`, base main
`9621024fcced776f157bd68471a4995c38f7dfd7` (includes L16/S3 and R3).
[Machine-readable receipt](author-acceptance.json), [protocol](PROTOCOL.md),
[geometry amendment B](AMENDMENT_B.md), [history amendment C](AMENDMENT_C.md).

## 1. What changed

`resense/clustering.py` exempts an observed collision core from **only** the
column shape signature. It does not reason from an absent/free upper surface:

* At least8 current occupied voxels, vertical span>=2.2 m, lowest<=1 m;
  observed horizontal footprint<=0.8 m in both dimensions.
* Supporting points must pass ordinary strict membership, rail membership, and
  the **rail-relative polygon with an additional0.30 m erosion**, retaining its
  range-growing margin. Accumulated old points cannot supply the current core.
* The raw frame independently supplies four near/local boundary profiles:
  left/right x two height bands. Every profile must have supported near and local
  bins. Its continuation hypothesis includes its full observed spread plus0.10 m.
  Keep the hull of every hypothesis and the fitted axis. The core must remain
  inside the eroded polygon at both hull endpoints; missing support gives no exemption.
* This hull is a **consistency guard, not a calibrated true-axis error bound**.
  It shares the near rail anchor and cannot resolve a common-mode anchor error.

`resense/detector.py` supplies the current cloud/coordinates for that guard.
`resense/tracking.py` allows a freshly reconfirmed positive-core run to suspend
only the old column hold: the run independently meets ordinary `confirm_hits`
and `confirm_time_s` (five10 Hz scans/0.5 s at defaults). A miss, non-core or
continuation resets it. The old measured column history is **not erased**;
60% zone vote, explained-run, doubt, confidence and ego guards remain.

Four geometry parameters are mirrored in the dataclass and both YAML files.
`column_core_margin=0` disables this candidate. The withdrawn free-top master
`column_free_max_top=0` remains unchanged.

## 2. Physical results and limits

The independent NumPy ray/AABB caster reproduces the exact archived case45 XYZ
hash,84 object returns,80 candidate voxels and20 rings. A second implementation
recomputes the four boundary profiles directly from raw NumPy point groups;
at67 m both implementations give exactly[-0.1,+0.1] m. A coherent displaced-
boundary positive control changes this interval as expected.
[Raw examples/calculation](physical-examples-plot-audit.json),
[inspected plot](physical-examples.png).

The full detector is also run on a separately specified physical scene with
idealized rail boxes (1.59 m centre spacing), without installing a truth track.
It estimates the rail pair, floor, orientation and axis itself.

| Check | Feature-off | Final C |
|---|---:|---:|
| Standing67 m, both sides, tops2.72/3.22/4.12 m and absorbing upper continuation |0 matched STOP|10/14 per case, after ordinary confirmation|
| All32 standing full-detector positive cases,896 paired frames |80 matched rows|230 matched rows, none lost|
| Fully outside bodies,48 component cases with supplied model errors within+-0.30 m |no new core/STOP|no core/STOP|
| Fully outside bodies, additional32 cases at+-0.60 m |not an acceptance budget|**5 gain a core and matched STOP**|

All32 full positive cases are rechecked from their saved detection positions,
not from the precomputed hit flag. **Nine cases remain entirely missed:**
at109 m the left body with top2.72/3.22/4.12 m; at137 m those three tops on both
sides. Absorbing-top bodies can be detected by the old shorter-body path; that
counterintuitive behavior is preserved rather than called a new improvement.
The larger-error false cases are at37 m both near-edge sides,67 m both sides,
and109 m left, physical lateral+-1.29 m; inner face is outside the1.05 m edge.
These are supplied coordinate-model errors, not measurements of their frequency
on real recordings. [Every physical case](physical-sweep-c.json),
[independent audit including every larger-error row](raw-audit-c.json).

### Moving opaque body: first STOP is not reliable100 m detection

At22 m/s (2.2 m per0.1 s), a4.12 m-tall body approaches from155 to34 m:

| Physical lateral | Original feature-off first STOP | Final C first STOP | Final C held90% |
|---|---:|---:|---:|
| -0.68 m |49.4 m|71.4 m|60.4 m|
| +0.68 m |49.4 m|60.4 m|62.6 m|

The71.4 m onset is followed by gaps. Held90% is recomputed from the recorded
visible rows, ordered near-to-far, with at least five rows. It is a pooled
coverage metric, not a guarantee against any individual missed scan.
The actual tracker return/gate trace on112 frames equals its matched plain
serialized control outside wall-clock telemetry; it shows the old column hold
and the unchanged vote, not a reconstructed explanation.
[Before history fix](moving-trace-b.json), [after](moving-trace-c.json).
**No100 m or stopping-distance sufficiency is established.**

## 3. Preservation checks on the final committed source

* **Full gate PASS**, original shell-off baseline, no overrides/waivers/missing
  metrics. Fresh base control,15,269 ordinary serialized rows +3,060 Set F rows.
  **All208 non-timing metrics and every normalized ordinary/Set F row are equal**
  to base main. Every previous detection payload and STOP is retained; five empty
  bags and the complete11,271-frame ride have zero added STOP.
* **X3 PASS:**40 cases,29,765 rows,260 comparisons. Independently reopened all
  raw workers, verified completion/source identities and hashes, and recomputed
  summaries. Every non-timing row equals the same-input base control, including
  all detections and warnings. No lost/added STOP or old detection payload.
* **Actual Falcon:** all4,443 node-replica rows equal base outside timing,
  preserving1,372 STOP rows and every warning/detection.
* **A-axis:**82->105 of177 visible matched rows, none lost; all27/27 visible
 60..100 m rows now match. First STOP stays218.38 m; held90% is only9.58 m
  because of remaining nearer gaps. Do not present218 m as sustained range.
* **C-person:**55 matched rows and82.77 m first STOP retained.
  **R3 E6:**34 matched rows,86.25 m first /61.28 m held retained. Hanging is
  unchanged in gate/X3; compact-int16 versus float32 sensitivity remains inherited.

The A-axis run adds **one unmatched STOP decision at frame335**, where target
X=2.41 m and no object returns are injected. Full assignment tracing confirms
`q=false`, `reported_before=true`, `misses=hold_misses=1`: ordinary one-miss hold
of the newly retained object, prediction2.37 m. This is below the3 m candidate
range and is not silently removed from unmatched statistics. All23 added visible
matched rows have saved tracker/assignment states.340 plain/traced frames agree
in every raw FrameResult field except timing and in every non-timing node field.
[Trace](axis-trace-c.json).

[Complete raw audit](raw-audit-c.json) also exercises the comparators with a
deleted known positive detection, an added empty STOP and a changed axis field;
all three planted differences are detected.

## 4. Tests and failures retained

* **284 affected tests PASS**, zero failures/errors/skips/deselections;
  [JUnit](units-c-final.xml). Physical/ring/duplicate/union/history/miss controls
  and the earlier tracking/free-top/structure/R3 guards are included.
* Full C pytest: **2,122 passed +17 subtests,2 failures,8 external-data
  deselections, no skips**. It is **not an all-green suite**.
  * `test_lidar_proxy_hook.py` expects a particular error message when the pinned
    source is missing. The same failure is reproduced on exact base main;
    [baseline witness](baseline-unrelated-test.xml).
  * Accumulation timing exceeded150 ms in the full run: p95=153.7 ms. In a
    separate sequential isolated check, base p95=17.7 ms, candidate p95=27.4 ms,
    both pass. The failed full-run sample remains; it is not a measured speed gain
    or proof that contention alone caused it.
    [Console timing note and retention limit](TIMING_NOTE.md).
* Ruff on changed production/tests and the evidence drivers; `git diff --check`.

Candidate A passed125 affected tests but failed the full gate: empty bags8->10
events /12->14 episodes; ride27->38 events /30->41 episodes,126->203 STOP frames.
Its sources/raw outputs are preserved. B added independent boundary hypotheses;
C fixed the moving-body history delay. An initial C unit wrongly assumed a50%
vote; corrected to preserve the actual60% vote, with its failed JUnit retained.

Harness corrections: initial X3 `-j3` was invalid (only1/2 supported); a20-minute
timeout later left39 completed reference workers and one partial worker. Only
the partial worker was rerun in a fresh folder; all40 completions were validated
before assembly. The first trace comparator accidentally compared `total_ms`;
the corrected run explicitly excludes that measured clock field and checks raw
outputs too. The first rail fixture confused inner gauge with centre spacing;
the corrected physical scene and its initial failures are retained. The first
outside example plot said “not fixed”; its corrected caption says “outside: no
STOP”, and the first plot is retained separately.

The initial fixture's error JUnit is preserved byte-exact in
[failed-fixture.tar.gz](failed-fixture.tar.gz): member `full-detector-first.xml`,
SHA256 `9e7cf873f89f1c26ec6a79e17918d2e13b4741e3c71f009242d21c1653991f9a`.
Its raw traceback has trailing spaces; storing the original XML in an archive
preserves those bytes while keeping the maintained text diff whitespace-clean.

## 5. Sources, reproduction and handoff

Measured C source fingerprint (38 frozen files):
`4953e8a8a24afddb4a8720ec95902ce884190b5af7b8c2712185040c5966c9cd`.
Every file is checked against the Git blob at `fd89712`. Gate/X3/critical-probe
receipts verify that source bytes are unchanged across each run.

* [Exact source/tests/native archive](final-source.tar.gz),
  [member manifest](final-source-manifest.json).
* [All raw runs, failures, logs and source snapshots](raw-evidence.tar.gz),
  [member manifest](raw-evidence-manifest.json). Every member was reopened and
  hash-verified; raw archive SHA256:
  `acd80ace43849faa3b417b07761bbc527f71fc36890d15fe5a1951a678b16545`.

Runtime: `/tmp/opencode/resense-b4-venv/bin/python`, NumPy1.26.4, existing native
SHA256 `67fa0887e5480e24ca67138ec5271969742917a5c5869d9ab4e634599d8c7394`.
Set `RESENSE_REPO`, `PYTHONPATH`, `OPENBLAS_CORETYPE=Haswell`,
`OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, and the existing library directory
`/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu` in `LD_LIBRARY_PATH`.
Original commands/environment/source hashes are in `*-execution.json`.

The drivers use existing caches in `/tmp/opencode/resense-b4-data` and the
registered R3 placement/ICP in `/tmp/opencode/r3-h1`. Use a clean checkout of
`fd89712`, copy these evidence drivers into the same relative folder, and choose
**fresh WORK/output names** when reproducing; archived outputs are immutable.
The gate and X3 drivers run the unchanged evaluation tools. `finish_reference.py`
documents the one-worker recovery instead of claiming a new uninterrupted run.

**P4:** review boundary-source independence, the common-mode0.6 m failures,
history suspension/reset, all retained/matched sets and the unmatched335 hold.
**P1:** decide scope only after that review and perform any baseline/reseal work.
**P3 next:** establish an independently validated near/far axis error budget and
recover reliable moving-body range; nine far misses remain explicit. The broad
High is open. No G3, new J1 score, ROS/DDS/image/release measurement or new seal.
