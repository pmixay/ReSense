# P4 branch-check follow-up and review handoff

P4's report checked **`b4235623327f084e84b2a8c582655548b29140c9`**. The later
**`cf188486f5c2339cd74adcb52ecdd21a59f8fad0`** contains the completed default gate,
X3 review and replacement development seal. Their 38 sealed source files are
identical. The historical seal failure is preserved; it was resolved after P4's
checked revision. A separate **unreleased 1.2.0 candidate**, committed as
**`e9d8fc649f2dd51dd5cd1e4b04ac8c306cc02569`**, has now passed its fresh complete gate.
The user selected **sealed main 1.1.0 for the next J1** and a separate review of
1.2.0. **Final P4 review of that candidate remains pending.** No
cross-member agreement, release approval or external message is claimed here.

## Preserved independent P4 check

The five files in [p4_original](p4_original) are exact Git-blob copies from P4's
commit **`1b880168ce2dbeec2071838892ac05eed5a9166a`**, originally under
`docs/evidence/p1_branch_check_2026-10-18/` on `origin/ccr-027997e8-kqywat`.
The [canonical original folder](https://github.com/pmixay/ReSense/tree/1b880168ce2dbeec2071838892ac05eed5a9166a/docs/evidence/p1_branch_check_2026-10-18)
retains that commit's link context.
The [intake manifest](p4_intake_manifest.json) records each source path, Git blob,
byte count and SHA-256. The [original report](p4_original/README.md), including its
FAIL wording, is unedited. Its relative dry-run link refers to its original
directory; the relocated target is [RELEASE_DAY.md](../rejudge_2026-10-16/RELEASE_DAY.md).

P4 reports **27 PASS, one seal DIFF, zero missing checks**: three complete
synthetic recordings (386/736/545 frames), all 4,443 Falcon frames, both switch
orders, gauge-range/honesty checks on ten recordings, and 24 automatic mounts on
two recordings. The one changed orientation case replaces a pre-adoption GO with
CAUTION. Rolled-90-degree cases still produce 395–509 STOP frames on the empty
recording and may report mount status `ok`; universal automatic orientation is
not established. These failures remain limitations, not resolved requests.

This independent execution used P4's judge node replica. It did **not** test the
actual ROS node/display, opt-in conservative range/replay policies, full gate or
X3 at that revision, and it is neither J1 nor final seal acceptance. The five
committed files reference external raw captures that are not included in this
intake. We verify their exact report bytes, not every underlying P4 frame.

## Requests 1 and 2: historical resolution and new-version work

| Item | Completed source evidence | Separate 1.2.0 candidate requirement |
|---|---|---|
| Replacement seal after the old verification failure | [38-file development seal](../detector_freeze_2026-10-18_lidar.json), committed in `ed6327f2a5f0048fbd52efed5ff59fe7de318871`; [actual manifest review](../lidar_adaptation_2026-10-18/default_off/MANIFEST_REVIEW.md) passes | Final candidate integrity manifest must bind its actual measured version and evidence. Preparing it is not final P4 approval. |
| Complete default gate | `fb7790039aeacf8cb4ed17a68609d649f806ee06`: [18,329-row gate](../lidar_adaptation_2026-10-18/default_off/gate.json), 15,269 ordinary and 3,060 Set F rows; all 805 ordinary STOP frames and 51 intervals preserved | **PASS on `e9d8fc6`**: [fresh 18,329-row gate](../version_1.2.0_2026-10-18/gate.json), exact shared non-timing parity and all STOP boundaries preserved; no overrides, missing rows or waivers |
| X3 and independent preservation | `113231d59557fb5bc5c50c76117a84b978264505`: [40 cases / 29,765 rows / 260 passing checks](../lidar_adaptation_2026-10-18/default_off/X3_REVIEW.md), all 6,284 STOP frames and 204 intervals preserved | Preserve these source identities; link the version-only continuity proof and whatever new final-source checks the reviewed candidate requires |
| Full actual Falcon | [Fresh matched-runtime comparison](../n2_falcon_2026-10-18/falcon_default_off/README.md): 4,443 rows, all 1,372 STOP frames/eight intervals preserved | Do not relabel the old capture as a new-version run; final review must state the exact source/continuity scope |

The completed evidence measures **`cecab1b696b8c2e101207601acd8faed96c8bfb8`**.
Its 38-file digest is
`5eae5197cc6497b029665a19e85b28fb217e934d8a80928cba6c1d2c5ad51700`; the
development-manifest SHA-256 is
`f75231a9d52124620ec7f23ee7ecf0050bf4e668ee2e10fdb660c3dba06bbc3c`.
All four package declarations at `cf18848` remain 1.1.0. That completed
development seal neither publishes 1.1.0 nor accepts the new 1.2.0 source.

The checker also proves that `e9d8fc6` changes exactly one `1.1.0` → `1.2.0`
declaration in each of the four version files. Two are inside the frozen scope;
all other checked runtime bytes remain equal. The only other changed paths are
`CHANGELOG.md` and the [new candidate plan](../version_1.2.0_2026-10-18/PLAN.md).
This proves source continuity. The fresh gate passes separately, with its raw archive
and [independent agent review](version_gate_review.json); final P4 review remains pending.

## Reproducible source continuity and gauge scope

The [checker](check_source_continuity.py) and [receipt](source_continuity.json)
compare immutable Git objects, not the mutable worktree. They require exact
inventories and file bytes for all 38 frozen paths, the complete ROS package
(node, launch, decoder, profiles, policy, gauge renderer and RViz configuration),
and the listed playback/display helpers. The gauge subset identifies both the
core envelope/configuration and the actual renderer/policy consumers. Overlapping
groups are counted once in the unique-file total.

```sh
python docs/evidence/p4_followup_2026-10-18/check_source_continuity.py \
  --out /tmp/p4_source_continuity.json
```

Two [rejection checks](intake_rejection_checks.json) confirm that changed copied
report bytes and a duplicated intake member are rejected. They use temporary
copies and leave the imported originals unchanged.

Identical node/display source does not mean P4 executed it. P4's replica range
and honesty metrics remain separate from the actual bounded visible gauge,
display smoothing and explicit range policy. The latter have their own
[installed-image/DDS review](../lidar_adaptation_2026-10-18/default_off/INDEPENDENT_DDS_REVIEW.md)
and [N1/N4 measurements](../n1_n4_2026-10-18/README.md). This checker runs no
detector, renderer, player or gate. Its historical equality endpoint stays
`cf18848`; the separate `e9d8fc6` section verifies only the exact version edits.

## Handoff draft and selected J1 target

The existing [ownership map](../../CAPTAIN.md#8-ownership-map-a-file-not-listed-its-authors-lane-ask-p1)
and [bundle plan](../../BACKLOG.md#4-order-up-to-the-defence-2310) assign P3 the
detector/native/config implementation, P4 independent measurement and safety
review, and P1 integration, the source seal and release. The original next bundle
was `det/1.2.0`; its dates were conditional. This is the documented division of
work, not a claim that the members have now agreed on a new handoff.

The user chose **sealed main 1.1.0 as the next J1 target**, with 1.2.0 reviewed
separately. The new candidate must not silently replace that J1 target. This is
a target selection, not evidence that J1 has run or that a release is published.

P1 has committed the four-file version bump and completed the fresh default gate. A
reviewable candidate integrity manifest is being finalized locally while hosted CI is blocked.
P4's final review should bind the exact candidate commit, source/config hashes,
complete gate and supporting frame-level evidence, with the readiness and
unsupported-sideways-mount limitations explicit. P3 should base any additional
detector work on the selected source; further changes need their own registered
tests and must join the final combined acceptance before a release decision.

A version-only bump changes sealed `resense/__init__.py` and `pyproject.toml`.
The [acceptance protocol](../lidar_adaptation_2026-10-18/PROTOCOL.md) and
[freeze procedure](../../DETECTOR_FREEZE.md#как-будет-принято-изменение) require a
full gate on the actual committed source. `create_manifest()` rejects files
that differ from the gate's measured commit. The [H5 precedent](../integration_2026-10-16/h5/README.md)
used both an exact version-only proof **and a fresh full gate** before resealing.
Old captures remain valid controls and supporting evidence; editing their source
identity is not an alternative to that gate.

The [API-derived CI receipt](ci_status.json), checked at **12:41:19 UTC on 18 October**,
records run `39125792924` for `cf18848`, check `117670520322`. GitHub's annotation
says the job did not start because of account payment or spending-limit settings;
the dependent Docker, pytest, offline-build and webapp jobs were skipped. The
short scheduled start/end timestamps do not establish test execution. That is
the observed hosted blocker, not a code-test failure or a claim about unobserved
future runs.

## Locally completed defect follow-up

The [orientation analysis and commands](orientation_analysis/README.md) reproduce the automatic
side-mount failure and derives explicit mappings for known ±90° mounts. Both full-recording
mapping controls restore the upright result: zero empty STOPs and all 193 real-obstacle
STOP frames, with identical non-timing payloads. This is a measured configuration workaround,
not a general automatic-orientation fix. The uncorrected control still has 509 empty STOPs,
two GO rows while wrongly confirmed, and six lost real-obstacle STOP rows; no such result is hidden.
[The independent result review](orientation_analysis/RESULT_REVIEW.md) checks all 2,984 saved rows.

The [curve crosswalk](curve_analysis/README.md) aligns B6 and N1 on identical visible points.
On those points, lateral error p90 worsens **0.799→0.896 m** after display smoothing.
The lower whole-visible-range error fraction mainly comes from showing less range, not
correcting curvature. C has no saved N1 display replay. [P3's concrete handoff](curve_analysis/P3_HANDOFF.md)
separates L10/K2 curve bias from K1 standing-train jitter and retains prior rejected changes
and the existing acceptance criteria. No automatic mount or curve-axis runtime patch is shipped here.

Keep candidate integrity, final P4 acceptance and publication distinct. Hosted
CI repair, tag/archive publication, release verification and release-specific J1
execution remain deferred; the next J1 source target is now selected. Neither this folder nor a locally
prepared manifest grants approval to publish. N3 robustness and N6 range targets
remain failed/off, the replay4 default remains rejected, and existing Windows
Set O frame 332 provenance and physical-ground-truth limitations remain open.
