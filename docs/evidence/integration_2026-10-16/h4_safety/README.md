# H4 independent object-safety review — BLOCKED

**One high and two medium object-safety findings block H4.** This is an independent
safety review, not release approval. The reviewer authored none of the production
code reviewed here. `BLOCKED.md` records the findings, source lines, witnesses and
reproduction commands; the initial blocked status was written before any author fix.

The committed `PROTOCOL.md` at **e39a011** was adopted without alteration.
Execution details and follow-ups were registered in ADDENDUM_01–04 before their
respective measurements. No G3 heldout specification, windows, cases, seeds or
shapes were read or used. The review writes only this evidence folder and its
dedicated external scratch.

## Reviewed and measured identities

| Identity | Value |
|---|---|
| Review target | `7cc640fb39698b1fe45bc6ab069eab68ad4ac6ae` |
| Measured candidate, actual detached Linux HEAD | `f8c088dc4f3243fbd15a3aae9be0459e8a0aa941` |
| Measured sealed control, actual detached Linux HEAD | `707ea9cda051369326fb9407c42488c1033dad76` |
| Candidate sealed-scope source digest | `a34cb1612f3f212d063370ebe0ad8648657aa15b62d751a69964eb1c825d3618` |
| Control sealed-scope source digest | `075a20df9fcdba6605a92e6505ae4dfdb3bf410ec09d17a8b3c79ce714db9292` |
| Native `.so`, both sources | `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534` |
| Immutable Linux tools image | `sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19` |

Every worker asserts the imported `resense.__file__`, explicit `PYTHONPATH` /
`RESENSE_REPO`, actual Git HEAD, native enabled/binary hash, clean LF bytes, effective
configuration and all **36** source files against actual Git blobs. Candidate blobs
are additionally checked against the target SHA. The H3 retained Linux source
volumes, common Git objects, cache and retained H3 outputs are read-only mounts.
Numerical threads=1, PYTHONHASHSEED=0, at most one H4 worker active at a time,
2 GiB memory limit. All **nine** worker containers exited 0, `OOMKilled=false`.
Full commands, mount modes and final container states are in `results/runtime.json`.

Exact per-return input/label/ring/dropout-mask hashes and per-frame cache byte hashes
are retained externally. Paired input identities match for **1,576 physical scenes**,
**144 surface components**, and every **3,947-frame** real control/candidate pair.
Configuration and source inventories are in `results/{sealed,candidate}-identity.json`.

## Findings

### H4-S1 — high: tall physical collision objects remain columns

At `resense/clustering.py:1007–1019,575–588,663–665` and
`resense/tracking.py:118–140`, a free pole continuing above the candidate-height
cut is retained as a structural column. The shipped tall-following option is off.

Independent ray case **45**, highest-first IDs, no dropout: pole width/depth
**0.46 m**, physical top **3.22 m**, distance **67 m**, lateral **+0.68 m**, ceiling
4.12 m. Its entire lateral body is inside the known physical envelope. There are
84 pole returns, **80 strict-gauge voxels / 20 rings**, observed candidate top
2.939613 m, score 1.0. **Zero matched STOP frames of 20** in either source; frames
9/10 intentionally omit the object. The shorter 2.72 m candidate control is detected.

This is a confirmed inherited collision-object miss, not a new regression and not
an uncertainty in fitted-axis ground truth. The registered review explicitly
requires assessing inherited tall misses. It remains blocking.

Witness: `results/tall_miss_witness.json`; input XYZ SHA-256
`680878ed4f0b233cec517f999ca8648b1193522c929b7ce0f9df9fad7d545a20`.

### H4-S2 — medium: free-top STOP does not re-arm on strong returning evidence

`resense/tracking.py:664–667,436–448`: the first uncorroborated spare is recorded as
a column explanation. After a confirmed STOP releases on two missing frames, that
old explanation can make the first clean returning observation advisory.

Ray case **44**, same position/width, top **2.72 m**: STOP frames **5–9,12–19**.
At frame **11**, all **72 strict-gauge voxels / 18 rings** return, score 1,
confidence **0.85**, candidate `zone=gauge, reason='', spared=true`, no column hold,
and 9/10 gauge votes. Yet `explained_hist` still contains the initial false-column
explanation, `clean_run=1`, `fresh_blocked=true`, final zone `warning`. Frame 12
returns to STOP after the old explanation ages out.

All 712 pre-dropout STOPs hold frame 9 and release frame 10 as configured; **268**
fail to regain STOP on frame 11, and all 712 are STOP on frame 12. This added 0.1 s
gap after evidence returns is a separate safety concern from the intentional
missing-hit release. It occurs in the newly recovered-object path; it is not
misrepresented as a lost sealed STOP frame.

Witnesses: `results/rearm_witness.json`, `rearm_delays.json`, `hold_release.json`.

### H4-S3 — medium: exact inherited dark-band excess is confirmed

`resense/clustering.py:574–592` and `resense/tracking.py:656–667,118–140`:
deleting observation-only continuation can promote real column tracks; repeated
spare corroboration does not remove the residual sensitivity, and old gauge votes
can retain STOP even after the current candidate has an advisory reason.

| Fresh-detector development ride piece | Plain sealed | Plain candidate | Exact inherited dark mask | Excess STOP frames |
|---|---:|---:|---:|---:|
| 1, 1,409 frames | 14 | 14 | **23** | **9** |
| 3, 1,409 frames | 2 | 2 | **7** | **5** |

No sealed STOP frame is removed. All **14** extra detections geometrically match
plain sealed warnings with **exactly identical serialized centers**, independent
of track IDs. Piece 1 excess is `new_data_27_0048`, `new_data_37_0049..0050`,
`new_data_38_0000..0005`; piece 3 excess is `new_data_99_0014..0015`,
`new_data_99_0029..0030`, `new_data_106_0047`.

The initially registered wider observer mask measured **9 + 10**, retained as a
separate experiment. After inspecting only the archived H1 mask definition, a
separate exact inherited-boundary replay was registered and independently
implemented; it confirms the published **9 + 5**. Neither result is substituted
for the other.

These are explicitly **artificial observer sensitivity** replays of obstacle-free
development footage, not unedited real-scene measurements or physical-ray false
positives. The cloud, fitted model and candidate point arrays are not deleted or
refitted. The result is still a confirmed medium robustness blocker under the
registered criterion; an unchanged plain gate does not waive it.

Witnesses: `results/dark_inherited_{comparison,track_matches}.json`, external
`run-001/exports/dark_inherited_witnesses.json`, and `real_comparison.json`;
each extra frame retains pre/post spare processing,
candidate geometry and all tracker qualification histories.

## Other measured results

### Physical ray scenes plus the shipped tracker

New slab-intersection ray caster, nearest opaque/absorbing hit, specified Pandar
grid and phase, true straight axis / physical envelope, distances 37/67/109/137 m,
both widths, all lateral centers, ring-ID modes and dropout masks. Ground truth
is never taken from a detector-fitted axis. Clustering receives known physical
corridor coordinates: this is clustering + tracking, not an end-to-end axis claim.

There are **1,576 scene variants per source, 31,520 tracker updates per source**,
plus 32 corrected beam-dropout variants per source. Candidate matched STOP frames
versus sealed (original 1,576 variants, corrected report-state interpretation):

| Scene group | Sealed | Candidate | In-envelope variants with no candidate STOP |
|---|---:|---:|---:|
| Top 2.72 m | 840 | 2,608 | 0 / 192 |
| Top 3.22 m | 780 | 1,144 | **112 / 192** |
| Top 3.62 m | 780 | 780 | **140 / 192** |
| Ceiling-height column controls | 780 | 780 | 140 / 192 |
| Absorbing column band 2.54..3.18 m | 1,680 | 1,680 | 80 / 192 |
| Absorbing column band 2.54..ceiling | 1,680 | 2,616 | 8 / 192 |
| Over-top beam controls | 0 | 416 | 0 / 32 |
| Multiple columns, per matched object | 120 | 120 | 16 / 24 |

These denominators include ring/dropout repetitions, not independent statistical
trials. Physical absorbing bands extinguish the nearest hit without replacing it
by background. They demonstrate sensitivity to actual return loss, but an
in-envelope synthetic column is itself a physical collision object: these STOPs
are not called physical false positives. The beam controls occlude upper
observation rays; they do not establish coverage of every fully occluded target.
No matched sealed STOP frame is lost in this sampled matrix. That relational
result coexists with H4-S1's inherited misses and H4-S2's returning-hit gap.

### Surface cut, span support and low duplicate ordering

**144** independent analytic components, mirrored/reversed, one/two echoes:

| Front residual | Cut parts | Spared parts | Matched STOP frames sealed -> candidate |
|---|---:|---:|---:|
| 1.12 m | 16 | 16 | 384 -> 752 |
| 1.36 m | 48 | 48 | 384 -> 1,488 |
| 1.64 m | 40 | 16 | 768 -> 1,392 |

All **104** emitted cut parts have shortened bottoms relative to their full
sampled attachment boxes; none has a shortened top. No matched sealed STOP frame
is lost. Width and connecting side surfaces can cross the residual bar even when
the nominal front residual is below it. These supplied-coordinate components do
not prove physical ray realizability or complete-body recovery.

The corrected direct H2 span fixture rejects single columns and actual
**0.099000004 degrees**, accepts **0.100000009 / 0.101000013 degrees** with 22
voxels, identically for one/two echoes. The initial x=111 fixture was inconclusive
because it did not clear the residual bar; its outputs are retained. No assertion
or production threshold was relaxed.

The actual duplicate filter followed by actual tracking shows the constructed
newly spared cut part suppressing a low cluster on frame 0, then being demoted by
spare corroboration. Low-only control first STOP is frame 4; with the part it is
frame 5. This is retained as a **constructed ordering concern**, not a separately
confirmed physical blocker: its empty corridor-foot input and simultaneous low
geometry were not realized in a full physical scan. Surface components do produce
spared cut parts, but that alone does not realize the whole low-obstacle witness.

### Complete real development stress and H3 provenance

| Replay | Frames/source | Sealed -> candidate STOP | Detection/warning descriptor differences |
|---|---:|---:|---:|
| B, 27% dropout, seed 461023 | 252 | 0 -> 0 | 0 |
| S, same independently generated dropout seed | 877 | 51 -> 51 | 0 |
| Plain ride piece 1 | 1,409 | 14 -> 14 | 0 |
| Plain ride piece 3 | 1,409 | 2 -> 2 | 0 |

STOP and warning frame sets match exactly, not just counts. Both plain ride pieces
for **both** sources reproduce retained H3 serialized non-timing outputs with
**zero mismatches**. There are 13,530 total real detector frame calls including the
two dark-mask variants. The stress replays retain complete original receive stamps.

At `new_data_54_0009`, candidate distance 73.5599976 m, n=25, ring_count=17:
pre/post spare stays gauge with empty reason, prior spare history
`[false,false,true,false]`. The track is located by actual **`t.last is c`** and is
**422**. Column history `[true,false,true,false,false]` still holds it advisory;
zone history `[false,false,false,false,true]` votes warning; it is unreported and
in neither output list. Obstacle=false, nearest=null, clear=44.6 m. This confirms
the H3 explanation independently. See `results/promotion.json`.

### Azimuth cache

**80,000 float32 returns, 150 windows**, seed 461029, including front/back, x=0,
and bucket boundaries: **zero** return-index differences against the independent
brute-force float32-product oracle. See `results/azimuth.json`.

## Audit, reproduction and retained evidence

`COMMANDS.md` lists execution and derivation commands. `launch.py` uses the exact
retained H3 volume names from HANDOFF; full Docker argv are retained per worker.
Use a fresh `--run` name to avoid overwriting a prior measurement.

External root (all large raw JSONL, original summaries, logs and launch records):

```text
C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-h4-safety-20261016\run-001
```

`results/EXTERNAL_ARTIFACTS.json` indexes raw bytes/hashes. `HASHES.json` indexes
the compact package. Larger derived physical case lists, paired dark frames and
surface case lists are in external `run-001/exports/`, also hash-indexed.
All production sources were mounted read-only; no core,
version, manifest or other review folder is edited by this review.

Two probe-adapter issues were found and retained transparently (ADDENDUM_02/03):
the initial span geometry did not isolate its bar; initial component STOP fields
mistook `Tracker.update()`'s all-track return list for reported tracks. Every raw
frame preserved actual `reported` and zone, so `derive.py` recomputes all final
STOP sets from immutable snapshots. Original component `stop_labels`, `stop_ids`
and `*-summary.json` are invalid as STOP counts; `*-derived-summary.json` is used
for all initial-matrix comparisons. Corrected follow-up workers use the fixed
adapter. Original beam dropout removed its beam too; a separately registered
target-only dropout replay confirms the same aggregate counts. The first two
workers predate the reviewer-script-hash observer; all nine have full production,
native, config and input identity checks, and later workers retain reviewer hashes.

`results/verification.json`: artifact integrity **PASS**, safety verdict **BLOCKED**.
Passing artifact checks establish trustworthy evidence, not detector acceptance.
