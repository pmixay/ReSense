# 1.2.0 candidate preparation after P4's development check

Registered before the new version's measurements on 18 October 2026. The user's request is
to complete the locally actionable P4 follow-up, continuing `work/n5-labels-c2-acceptance`.
Release remains deferred until CI is repaired and the team accepts a selected version.

The captain selected **sealed `main` 1.1.0 for the next P4 J1 evaluation**, with this
1.2.0 candidate reviewed separately. This preparation does not move that evaluation target.

The selected starting tree is `cf188486f5c2339cd74adcb52ecdd21a59f8fad0`, with the detector
bytes measured at `cecab1b696b8c2e101207601acd8faed96c8bfb8`. P4 checked `b423562` before
the full gate, X3 and updated development seal were committed. Its report at `1b88016`
explicitly is a development check, not final seal acceptance or J1.

This preparation changes only the four package version declarations from 1.1.0 to 1.2.0,
plus documentation and evidence. It adds no detector, node, configuration or display behavior.
Replay remains opt-in, N6 extension remains off and no production dust observer is enabled.
L16 and curve bias remain reported defects; they are not silently included as fixes.

1. Commit the synchronized version declarations and changelog before measuring.
2. Independently compare all source/build/node/display files against the previous accepted
   development tree and P4's checked tree. Permit exactly the four version substitutions.
3. Run the complete default regression gate on a detached checkout of that committed version:
   six recordings, Set O, full ride and all 30 Set F sequences, without waivers or overrides.
   Use the same Haswell BLAS dispatch, one thread, verified cache and native library.
4. Reconstruct all gate summaries from raw output and compare every shared non-timing row
   against the already accepted default-off run. Retain any failure and all STOP boundaries.
5. Existing X3, full Falcon, actual Docker/DDS and display runs keep their original source
   identities. They are supporting continuity evidence, not newly executed version-1.2.0
   captures. A runtime change would require fresh affected batteries and P4 review.
6. Prepare a hash-bound candidate integrity manifest only after the fresh gate and review.
   This identifies reviewable bytes; it is not P4's final acceptance or authority to publish.
   The handoff must explicitly retain **P4 approval pending**, no new J1 score and no release.
7. Supply the exact measured source and evidence commits to P4, plus the source-diff proof
   and remaining defects. P1 remains the single integration/seal owner; P3 owns follow-up
   detector patches. Coordination is proposed until P3 acknowledges it.

The standalone P1 map stays outside the repository. No new branch, tag, release or external
message is created by this preparation.
