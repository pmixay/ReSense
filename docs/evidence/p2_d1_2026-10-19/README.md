# P2-01 / D1 reconciliation — 19 October 2026

**Scope:** execute the first package in `docs/ROLE_2_PLAN.md` (§4 P2-01), using
existing evidence. This receipt reconciles documentation and provenance; it does
not rerun the detector, issue a release, change scores, or record owner approval.
Starting checkout: `6bcd2e3`, branch `ui-improvement`.

## Plan-to-deliverable acceptance

| Registered requirement | Delivered / checked | Disposition |
|---|---|---|
| 1. Refresh P2 status and maintained launch/output docs; preserve history | `web/P2_STATUS.md`, `web/DEMO_HANDOFF.md`, root README, CAPTAIN, docs index, GitBook launch/output/prototype and webapp README distinguish current candidate, selected J1 source and published release | PASS for this checkout; public GitBook publication follows merge/sync |
| 2. C1, version, branch/review state, demo ownership, measured media duration | C1 producer/consumers are implemented, not absent; current package 1.2.0 replaces CAPTAIN's stale current-1.1.0 statement; P1 owns pitch/rehearsals, P2 supports visuals/devices; ffprobe and frame-count/rate both give 180.000 s | PASS; historical 2:50 records retain their dates |
| 3. Trace current headlines, exact source, pipeline, scope, denominator and machine | Source map below; `check.py` independently hashes all 38 frozen files against the measured Git blobs and working tree, reconstructs gate/X3 counts from detailed receipts, checks all five raw archive hashes, and rechecks the score/video | PASS; this verifies stored receipts, not a new evaluation |
| 3. Residual DATASET dual-return and EXPERIMENTS ownership | Maintained DATASET already records the 193→189 STOP and 51→11% CAUTION effects; no residual “no decisions change” claim was found there. EXPERIMENTS/score values are left with their source owners | Existing correction confirmed; new captions still require P3/P4 numeric review |
| 4. P4 chart-input agreement and P1 marker request | Existing verified P4 export v1 intake is accepted; 18-slide source-backed draft exists. Updated owner requests are in HANDOFFS.md | Technical intake complete; P1 final-image marker/media and P4 merged-source acceptance remain owner-pending |
| Done: stale-claim search and relative links | Exact searches distinguish dated history, backlog descriptions and current claims; changed-document relative targets checked by `check.py` | Receipt in `checks.json`; historical links outside the changed scope are not silently rewritten |

## Authoritative source map

| Current statement | Source / exact identity | Scope and interpretation |
|---|---|---|
| Published reference remains v1.0.0 | local tag `v1.0.0` → `5d6e9b5`; archived release/judge receipts in SCORECARD | Local tag and stored evidence checked; no fresh download or GitHub publication verification claimed |
| Current checkout package is 1.2.0, not released | `scripts/release_meta.py version`; four package files | Package identity, not a release or score |
| Current B4 merged source/seal | `../b4_merge_reseal_2026-10-18/acceptance.json`, measured `0779db74beddc07fcb8cb89cda6e2837e31e4d62`; fingerprint `68dee667…`, 38 files | Integrating-agent paired acceptance, one-CPU shared host, Python 3.12.3 / NumPy 1.26.4 / Haswell BLAS; no throughput gain inferred |
| Gate / X3 / orientation coverage | Detailed frame reviews and B4 summary alongside acceptance.json | Gate: ordinary node/cache rows and Set F scoring rows remain separate; X3 is in-sample; B4 uses transformed Pandar inputs. No G3 or universal mount guarantee |
| Earlier actual DDS and software-RViz results | `../n1_n4_2026-10-18/README.md`, selected-default `cecab1b`, image `eb53df868b16`; graphics comparison uses its separately named earlier source | 140 input frames in one node; software RViz uses 70 curve frames at rate 0.5 on one CPU. These are not tests of the later merged `0779db7` image or full S5 |
| Current independent score | `../judgement_2026-10-13/scores.json#/total/score`, measured commit in that JSON | 66/100 for release-equivalent v1.0.0. No increase inferred from UI or candidate checks |
| Selected J1 source | root README and `../p4_followup_2026-10-18/README.md` | Pinned 1.1.0 `3b7d7aa`; current 1.2.0 checkout does not replace P1's selection |
| Chart input agreement | `../p2_execution_2026-10-16/P4_INTAKE.md`; `../../presentation/draft_2026-10-16/manifest.json` | Existing long-form v1 export, complete register/raw delivery accepted; draft is prerelease/in-sample, final J1/P1 sign-off pending |
| Overview video | `../../video/resense_overview.mp4`; ffprobe format duration and video frames/rate | 180 s, H.264 1920×1080 with AAC; historical media, not a new release-matched recording |

## Preserved decisions and outstanding external inputs

The export has expanded since the dated 16.10 intake: current `--check` reports
**343 registered cases / 3,396 numbers (146 derived), zero mismatches**. This D1
check independently resolves every non-derived number against its hashed source
and JSON pointer and compares the register's CSV/JSON row counts. The earlier
238-case / 2,461-number receipt remains historical; the draft deck is not silently
relabelled as using this newer export or a final J1 result.

H1/free-top remains withdrawn, S1 failed its registered runtime acceptance, C1-v2
remains rejected, startup replay is opt-in/default 0, experimental dust suppression
and N6 remain off. Earlier candidate reviews keep their original source IDs;
P4's `6cc27be` gate objection is not relabelled as an approval of merged `0779db7`.
The later paired merge gate is present, while final P4 merged-source acceptance
and release authorization are explicitly pending in acceptance.json.

There is no new rehearsal/device log, selected-release S5 matrix, O1 decision,
final PDF approval or new release/J1/G3 receipt in this checkout. Those are not
marked done. The complete final-stage P2 plan therefore remains open even though
this first reconciliation package is implemented and mechanically checked.

Run the receipt check from the repository root:

```sh
python3 docs/evidence/p2_d1_2026-10-19/check.py --out docs/evidence/p2_d1_2026-10-19/checks.json
python3 scripts/detector_freeze.py verify
bash scripts/sync_params.sh --check
```

No sealed detector/configuration/native files are modified by this task.

### Live public-release lookup

The unauthenticated request to `https://api.github.com/repos/pmixay/ReSense/releases?per_page=5`
returned **HTTP 404** on 19.10. This does not establish whether the repository is
private, renamed or otherwise unavailable. The local `v1.0.0` tag and archived
release receipts remain verified locally; current public release/asset visibility
is **unverified**, handed to P1 rather than presented as a successful fresh lookup.
