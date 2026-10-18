# Working rules for Claude in this repository

## Verify results, do not trust your own scripts

A number, label or "found nothing" printed by a script you just wrote is a claim, not a result.
Before reporting it, or building on it, check it:

1. **Against an independent source.** Re-derive the key result another way: from the raw points
   instead of your transform, with a second method (for example odometry from ICP vs. object
   steps), or against a case with a known answer. Example: intensity-1 "marker" labels looked
   plausible, but checked against an exact reference they found 57 % of the objects and made
   about 12 false objects per frame.
2. **With a positive control for every negative result.** "0 matches", "no dust" or "no
   difference" counts only after the same tool, on a case where the answer is known to be
   non-zero, finds it. Example: the source-frame search was trusted only after it matched
   252/252 frames of a known bag.
3. **Every label, not just its presence.** When rows get a cause or category, confirm the
   label from the full state (snapshots) on all rows, or on a stated sample per category.
   Record which branch or rule actually fired (trace it) rather than reconstructing it afterwards.
4. **By looking at the data.** Print or plot a few raw examples (`frame_*.png`, a few rows)
   and check that they show what the numbers say.
5. **For physical plausibility.** Speeds, sizes, distances and counts must make sense
   (a train does not move 3 m in 0.1 s; a person is about 1.7 m tall). An implausible value
   is a finding about the data or a bug in the script; find out which.
6. **Instrumentation must not change results.** A traced or hooked run must equal a plain
   run (every field except wall-clock timing) before its attribution is used.

When you report, say what was checked, how (method, how many rows or frames), and what failed
or was corrected. Anything not checked is reported as unverified.

## Practical traps in this container

* `pkill -f` / `pgrep -f` with a pattern that also appears in your own shell command matches
  that shell (exit 144, or a wait loop that never ends). Use a wrapper script or a PID.
* Background commands are killed at their `timeout`; give long jobs an explicit long timeout
  and write their output to a log file.
* Evidence runs: set `RESENSE_REPO` to the checkout being evaluated and
  `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1` (P4 protocol, amendment 1).
* Never modify detector code (`resense/`, `native/`, `configs/`, the ROS package) for an
  evaluation; never run or touch the held-out G3 set.
