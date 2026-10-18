# Independent review of the actual 1.2.0 candidate integrity manifest

The [actual candidate manifest](../detector_freeze_2026-10-18_1.2.0_candidate.json)
passes the independent [checker](review_candidate_manifest.py), with its full
[receipt](candidate_manifest_review.json). Manifest SHA-256:
`99b1f8e079a37a875feb098ebc67107c5f6a1ada7327a3ce95c5875339f74caa`.

All **38 frozen source files** match measured commit
`e9d8fc649f2dd51dd5cd1e4b04ac8c306cc02569`, committed evidence revision
`abc16e326e01317b2fbc2bf82ab20fda544637d6`, and the current worktree. Their combined
source digest is
`b85a93064e79e932df4f7045af21effdf43f0858963204db5d30fc1de37a5e3a`.
All **17 supporting references**, the baseline, the fresh gate and the previous
manifest match their recorded hashes and committed Git bytes. The checker also
rehashes the transitive inputs of the new gate reviews and the historical joint
acceptance/X3 archive reviews. Built-in verification reports no errors.

The manifest retains the old authorization, decisions and limitations. Startup
replay remains opt-in with default 0, the N6 rail-axis extension remains off,
and no dust-suppression candidate is enabled. The old X3, full Falcon and DDS
captures retain their `cecab1b` identity; the exact version-only proof and the
fresh 1.2.0 gate provide separate, correctly identified evidence. This review
does not turn the old captures into new-version executions.

The manifest is explicitly **candidate integrity only**. Its standard `frozen`
status means byte integrity, with **P4 final acceptance pending, P3 coordination
acknowledgement pending and release authorization false**. Sealed main 1.1.0 at
`3b7d7aa` remains the user's selected next J1 source. The manifest is suitable for
that separate candidate review; it neither completes J1 nor approves publication.

This review imports the existing configuration reader but runs no detector or
gate. Reproduce it with the project environment:

```sh
/home/resense/.venv/bin/python docs/evidence/p4_followup_2026-10-18/review_candidate_manifest.py
```
