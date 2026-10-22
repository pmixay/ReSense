# B4 release acceptance: protocol, first P4 review, author response (18.10)

> **Purpose:** the protocol for accepting the B4 orientation-recovery candidate, the first independent
> AI review of it (disposition BLOCK), the author's response, and the acceptance runner. It does not
> hold the release measurements themselves.
> **Audience:** reviewers of the B4 chain, P1 (seal), P3 (detector) · **Owner:** lane not recorded in the folder
> (the P4 review is by "a separate AI reviewer", the protocol and response by the patch author, see below) ·
> **Language:** EN
> **Last verified:** 2026-10-22: file list, links and the numbers below checked against the named files ·
> **Status:** historical; the block was lifted later, see Caveats

## 1. What was run, when, by whom

* Date of the work: 2026-10-18 (all three documents are dated that day: `p4/verification.json` field `date`,
  title of `PROTOCOL.md`). The only git commit that touches this folder is `ddf5b63` (2026-10-18, a commit
  "Preserve P4 measured helper..."); there is no separate import date for it.
* `p4/`: review by "a separate AI reviewer, not the patch author and not independent human approval"
  (`p4/README.md`). It read a candidate at observed HEAD `3b7d7aa7cbbf238c21f84330497697da131b7cb9` with
  uncommitted detector files; branch name omitted. Lane P4 (the later audit calls it
  "the earlier AI review" ([audit](../p4_audit_b4_6cc27be_2026-10-18/README.md))).
* `PROTOCOL.md`: the prospective release protocol (base `3b7d7aa`, sealed reference checkout `1b88016`).
  `AUTHOR_RESPONSE.md` says it was committed at `0a68b11` "before this revision"; that SHA is not an object
  in this checkout (`git cat-file` fails), so it is unverified here.
* `AUTHOR_RESPONSE.md`: the patch author's answer to B1/N2 and the N1/N3/N4 limits. The author's lane is
  not recorded in the folder; the later audit calls the requester "P3".
* `run_acceptance.py`: serial acceptance driver (tests, gates, B4, X3). Whether it was ever run to completion
  is not recorded here; the later audit says "X3 was never run by the author (the driver refuses an
  uncommitted tree)" (`../p4_audit_b4_6cc27be_2026-10-18/README.md`).

## 2. Result

* The P4 review disposition is **BLOCK / NOT ACCEPTED** (`p4/README.md`, `p4/verification.json`
  `disposition`). B1: with `frames=5, obs_spacing=1, provisional_min_deg=10` on `doubleT_obstacle`, first
  STOP is frame 8 for the identity control and frame 9 for the recovered rotation 4, and frame 8 is a lost
  matched `person_crossing` frame (`p4/README.md` table; `p4/verification.json` `first_stop_control` 8,
  `first_stop_recovery` 9). B2: no committed-candidate gate pair or X3 pair existed at review close.
* The same review audited the author's archived default-config B4 evidence and found 35,808 frames
  with zero lost matched STOP frames (`p4/verification.json` `b4_frames`, `b4_jury_matched_stop_loss`);
  the review's own re-run of the new test file: 38 passed (`p4/verification.json` `independently_rerun_pytest`).
  That archived evidence is not in this folder.
* The author response claims B1 fixed (final calibration frame 5 to 4, STOP frame 9 to 8) and N2 fixed
  (three cone offsets, spacing >=0.005); it cites 57 directed tests and states that full acceptance "must be
  on the committed revision" (`AUTHOR_RESPONSE.md`). No result in it is a final gate or X3 result.

## 3. Supports

* The B4 acceptance chain for the 1.2.0 candidate: [`DETECTOR_FREEZE.md`](../../DETECTOR_FREEZE.md) (row for
  `detector_freeze_2026-10-18_b4_merged.json`, marked superseded by the 20.10 reseal), [`CHANGELOG.md`](../../../CHANGELOG.md)
  (entry "P4 accepted the merged B4 source `0779db7`"), [`BACKLOG.md`](../../BACKLOG.md) line 275 (card history).
  I did not find this folder name in DECISIONS.md, EXPERIMENTS.md, SCORECARD.md or VM_GUIDE.md.

## 4. Contents (7 files)

* `PROTOCOL.md`: prospective acceptance protocol (criteria: no empty STOP, 24 rotations, 208 non-latency rows, X3 limits).
* `AUTHOR_RESPONSE.md`: author response to B1, N1 to N4.
* `run_acceptance.py`: acceptance driver; `p4/` is the reviewer's own material:
* `p4/README.md`: the review (B1, B2, N1 to N4, audit results, commands).
* `p4/verification.json`: machine-readable disposition and hashes.
* `p4/audit_evidence.py`, `p4/directed_checks.py`: reviewer scripts (the second is the B1 reproducer, exit 1 on loss).

## 5. Caveats

* **Superseded.** B1 was closed on committed `6cc27be` by [the P4 audit](../p4_audit_b4_6cc27be_2026-10-18/README.md)
  (B2 gate part left open there); the merged source `0779db7` was measured and resealed in
  [b4_merge_reseal_2026-10-18](../b4_merge_reseal_2026-10-18/README.md) and accepted in
  [p4_review_b4_merged_2026-10-19](../p4_review_b4_merged_2026-10-19/README.md). The seal itself was later
  replaced by the 20.10 reseal. Pre-experiment history: [b4_orientation_fix_2026-10-18](../b4_orientation_fix_2026-10-18/README.md).
* **Missing here.** Raw gate, B4 and X3 outputs are not in this folder. `../h1_miss_audit_2026-10-20/manifest-before.json`
  lists untracked `b4_release_2026-10-18/b4-raw.tar.xz`, `b4-summary.json` and `directed.json` in this folder; they are
  absent here, and the corresponding records are in `../b4_merge_reseal_2026-10-18/` (`b4.tar.gz`, `b4_summary.json`, `directed.json`).
* The review quotes `/tmp/opencode/...` outputs that were not kept (only their hashes, `p4/verification.json`).
* The historical author protocol was not committed before the first measurements (stated in `p4/README.md`).
