# P4 check of P1's work branch, 18.10

`work/n5-labels-c2-acceptance` at **`b423562`** (41 commits on `main` `3b7d7aa`), checked out detached; native
library copied from the 1.1.0 tree (`native/` is byte-identical to `main`). Runtime of the P4 protocol
(`OPENBLAS_CORETYPE=Haswell`, one thread). No detector code touched. This is a check of a development branch,
not a seal acceptance or a J1 score.

| check | result |
|---|---|
| seal (`detector_freeze.py verify`) | **FAIL**: 2 added and 9 changed detector files, config differs from the freeze, while the version is still `1.1.0` ([freeze_verify_b423562.txt](freeze_verify_b423562.txt)) |
| new recordings (`run_new_recordings.sh`, all steps, against the 1.1.0 values) | **27 PASS, 1 DIFF (the seal), 0 MISSING** ([compare_b423562.txt](compare_b423562.txt)): all frames of the three synthetic recordings, platform person first STOP 44.0 m, all 4,443 Falcon frames (0 lost), both switch orders, gauge range and honesty on 10 recordings identical to 1.1.0 |
| orientation battery (24 mounts, `doubleT_obstacle` 201 frames, `roundT_squareT_pressureGate_squareT` 545 frames) | **23 of 24 mounts identical to 1.1.0 on both recordings.** Case 1: the one GO before adoption is now CAUTION (P1's readiness guard). **Rolled-90° mounts (cases 4–7, 16–19) unchanged: 395–509 false STOP frames of 545 on the empty recording, mount status `ok`** ([ana_p1_*.json](.)) |

Controls: the unrotated mount equals a plain `probe.py` run on 201/201 and 545/545 frames (193 and 0 STOP); the
comparison script reports `DIFF` on a doctored copy (1 changed frame of 736; [dry run](../rejudge_2026-10-16/RELEASE_DAY.md)).
Decoded caches were reused from the 1.1.0 dry run (decoder `fastcloud.py` unchanged on the branch); the
Falcon recording and switch inputs were downloaded and decoded fresh.

Meaning: with the branch defaults, the new detector code (dust modules, rail-axis extension, startup replay, all
off or opt-in) changes no decision on these recordings except the pre-adoption GO, which agrees with P1's own
records. Not covered here: the regression gate and X3 on `b423562`, P1's node-side changes (`detector_node.py`,
`decision_policy.py`, gauge display; this harness uses the judge's node replica), and the opt-in profiles
(conservative clear range, startup replay).
