The re-judgement's check of the P3 / P4 completion pass (SCORECARD section 0.8), 26.09 evening, on
judge A's machine (see ../README.txt) with the caches of the six recordings and cloud_with_fake_obj
(the ride cache had been removed: the gates run with --allow 'ride.*' --allow 'set_F_straight.*').
Head 1f8b8ff (detector code of fa18832). run.sh is what ran.

robustness_<mode>.txt    scripts/robustness_check.py --mount as_recorded | roll_3 | pitch_3, and --every 2
                         (5 Hz): five obstacle-free recordings 13 / 16, 14 / 16, 17 / 18, 10 / 10 events /
                         STOP episodes; under roll_3 doubleT_obstacle's mount stays 'pending' in 190 of
                         201 frames and the person and rail object are found as recorded.
start_offsets.*          scripts/start_offsets.py: the five bags from frame 0 / 10 / 20 / 30 / 40:
                         13 / 16, 13 / 14, 13 / 12, 10 / 11, 7 / 11.
gate_candidate_B_six_setO.json   --set tracking.near_escalate_voxels=8: PASS, only set O #4 2 -> 3 STOP
                         frames (first STOP 5.2 -> 7.1 m), inside 384 -> 385.
gate_union_six_setO.json --set gauge.axis_union=1: PASS, only set O #4 2 -> 9 (first STOP 18.2 m),
                         inside 384 -> 391.
Every number equals the pass's own (EXPERIMENTS 1p). tests/test_edge_axis.py: 10 passed.
