# Frozen continuity candidate: development comparison

The corrected **v2 development comparison passes with no regression and no measured gain**.
Baseline and candidate have identical public signals on all 1,152 detector frames (576 float
clouds replayed as float32 and compact16): STOP/matching flags, IDs, detection geometry,
clear distance, warning and offline decision. These stationary sequences do not contain
missing-return intervals; continuity gains require the separately registered dropout tests
and real replay evidence. This result does not establish new range or real generalization.

## Frozen implementations and inputs

| Role | Detector source SHA-256 | Effective config SHA-256 |
|---|---|---|
| Baseline | `29574d0f9ce5ae90749cd2d4a8c28bd7d2bf607f43a17fd494b0c10f8c662636` | `de5c7fd6dfa74c1e656af6e233efd625e3e552736534e32efa625e5e8ff57f47` |
| Candidate `ef1d8f50299d9ccbbf65fc4ad5519764615853f6` | `2389db97234b8c59ca4e5ebacf0eccffaba8ea44e97cdcbfe1df272864a5dab2` | `6a6e5d859a0c1a86adce91edf1e8a46cd35b4bee21c5876406f1071cf2eaa46f` |

The candidate was measured with its proposed defaults, including a 0.3 s low-evidence
continuation window. No candidate files were changed during measurement. The baseline was
replayed from the evaluation checkout's original detector/config; its documentation/tooling
commit differs from the historical v1 run, while detector/config bytes match exactly.

V2 was committed as `859cde5` before any new clouds were generated. The 576-cloud development
cache was generated using the `6732cb7` runner and original baseline source. After generation
completed, installed-package observer imports were repaired without relaxing actual evaluation
source checks. V2 replays use the `dc4d33e` evaluator bytes; reports retain the distinct generator,
evaluator, source, config, native-library and geometry-auditor hashes.

All work used one CPU affinity (`taskset -c 7`) and one OpenMP/OpenBLAS/MKL thread, sharing the
machine with other gates. No latency claim is made. No reserved split was generated or observed.

## V2 results

Every v2 positive body physically penetrates the known canonical envelope. The two low shapes
have 0.06 m vertical overlap in both splits. These labels were fixed before generation and
were not adjusted after seeing detector outputs.

The following values are identical for baseline/candidate and float32/compact16:

| Metric | Result per implementation and encoding |
|---|---:|
| Sustained positive sequences | 19/32 |
| Matched STOP / visible target frames, including confirmation | 228/512 |
| Positive sequences never detected | 13/32 |
| Unmatched positive STOP frames | 0 |
| Negative-control STOP frames | 0/64 |
| Visible target frames with GO and clear distance beyond target + 1 m | 208/512 |

The below-rail negative control has no STOP in either encoding. The 13 missed cases are both
rail_box sides at 100/150 m, both compact_box30 sides at 100/150 m, compact_box30 at the 50 m
edge, and both box50 sides at 100/150 m. All have visible target returns in every frame.

In float32, ten of those missed cases have no returns in the physically intersecting envelope
portion. The compact box at the 50 m edge and both box50 cases at 150 m do have physical-envelope
returns, so body visibility and envelope visibility must be reported separately.

**183/576 encoding pairs differ in the count of returns inside the physical envelope**, while
**0/576 differ in matched STOP**. Centimetre quantization can move near-boundary returns across
the canonical envelope floor. Identical STOP decisions do not imply identical geometric evidence.

## Historical v1 candidate check

The full 35-case v1 comparison also **passes with no regression and no gain**. All 1,120
baseline/candidate public frame signals are identical. Historical counts remain 19/32 sustained,
228/512 matched visible frames, 208 GO clear-distance flags, and 0/48 negative STOP frames per
encoding. The original v1 protocol, baseline report and labels were not changed.

Those v1 positive labels include eight boundary-contact cube cases. Of the 13 missed sequences,
five are boundary-only (80 GO flags) and eight have physical envelope intrusion (128 GO flags).
This annotation is not a new headline success rate or an organizer-policy verdict. V2 fixes
positive geometry prospectively; equal v1/v2 headline numbers cannot be called a detector gain.

## Physical-profile audit hardening

After both development replays completed, the physical return counter was changed to read
`case.physical_geometry.canonical_profile_m` saved at generation. It now rejects a missing or
invalid saved polygon. Future changes to a candidate's default gauge profile cannot alter this
independent measurement; the mutation and absence guards are covered by focused tests.

[The parity record](physical-profile-counter-hardening.json) verifies all 36 saved v2 profiles
exactly equal both measured implementations' effective profiles **and their actual class defaults**,
loaded separately from the baseline/candidate checkouts. It records old/new auditor hashes.
This hardening changes no v2 label, cloud, physical count or detector outcome; existing reports
retain the auditor hash actually used, and no detector replay was repeated for this change.

## Artifacts

- [V2 comparison summary](comparison-development-v2.json): complete gate result, per-encoding counts,
  public-signal differences and report-file hashes.
- [V2 baseline frames](baseline-development-v2.json.gz) and
  [V2 candidate frames](candidate-development-v2.json.gz): full public detections, decisions,
  health, physical-envelope return counts and source/config identity.
- [V2 input manifest](development-manifest-v2.json.gz) and
  [historical v1 input manifest](development-manifest-v1.json.gz): exact per-frame cloud digests,
  seeds, labels and generator identity; cloud binaries remain local outside Git.
- [V1 candidate comparison](comparison-development-v1.json) and
  [candidate frame report](candidate-development-v1.json.gz), paired with the unchanged
  [historical baseline frame report](baseline-development.json.gz).
- [V1 diagnosis](diagnosis-v1.md): unchanged historical labels plus independent physical-body
  interpretation and 448-frame stage-observer parity.

Summary report hashes refer to the linked gzip artifact bytes. Cache-manifest hashes inside
replay reports refer to the original uncompressed JSON; decompress the manifest before checking.
