# Independent review, round 3: engineering, launch, method, pitch (8.5–8.8) — commit `fcbb3f8`, 23.09

The report of the reviewer who judged criteria 8.5–8.8 and the §7.2 deliverables (content unchanged,
lightly reformatted). The
reviewer had no stake in the work, was told to distrust the team's claims, worked from a
`git archive` export of `fcbb3f8`, built the image and ran the organizers' procedure on rebuilt
real bags (node container on the default command, `ros2 bag play` as uid 1000 from another
container), and deleted everything it created. How each finding was checked and what was done
about it: [`../SCORECARD.md`](../SCORECARD.md).

---

1. SCORES

8.5 Technical quality — 7.5/10. Well engineered, but the node behaves worse through ROS than the
offline evaluation shows. Evidence: a pure-Python library plus a thin ROS node, one config file
whose copy CI checks; `pytest -q` 150 passed in 43 s, `ruff check .` clean; the node has guards
(watchdog, FAULT/NO_INPUT/STALE, a reset after errors) and ALGORITHM.md §6 lists its limits; it
switches inputs correctly (two recordings with different topic/frame pairs into one running node,
both verified). Held down by: CI red at this commit (the web test, finding 1); false-alarm results
that depend on the frame processing starts from (finding 4); several stale docs; a 360° cloud
takes ~100 ms through ROS on 4 vCPU, so 25–35 % of the frames are dropped.

8.6 Ease of launch — 8/10. The organizers' chain works as written. Evidence: the node ran on the
image's default command with no arguments; `ros2 bag play` ran from a separate container as uid
1000, with the image's DDS profile and with stock Fast DDS (standing in for a host console), with
and without `--delay 3`; `/resense/decision` gave STOP at 55.8–56.5 m on doubleT_obstacle;
switching to /lidar_points worked; with stock kernel socket buffers (rmem_max 212992) it still
worked, at 127 of 201 frames. Held down by: the first 2.0–3.9 s of every played bag are never
processed; the team's own acceptance scripts fail as written; the jury path starts at line 170 of
a 407-line README; no prebuilt image artifact in case the test stand is offline at build time; on
an empty tunnel CAUTION is the most common decision.

8.7 Team approach — 8/10. Unusually honest and quantified. Evidence: EXPERIMENTS.md §7, a table
of 10 methods with verdicts including rejected ones (a bed-anomaly stage with 1 482 events); the
learned "second opinion" of §8 not shipped after the team found a leakage (intensity comes from
the injector); false alarms broken down by cause, a leave-one-subset-out check, every number
labelled real or synthetic, and the trade-off of not reporting objects on the bed stated. Held
down by: the evaluation protocol always starts at frame 0, which misses the conditions the jury
will run under (finding 4); all long-range positives are synthetic; the story is spread over
~3 700 lines of docs full of version history.

8.8 Pitch — 7/10. A clear arc and the hero frame; thin visuals and video. Evidence: 15 slides in
the organizers' template (compared shape by shape against the downloaded template: slides 1, 2, 4
and 5 match template slides 7, 8, 10 and 11); the arc problem → data → algorithm → hero frame
(STOP at 55.8 m) → demo → results → range → hard cases; the cab video is strong. Held down by: all
four videos are 20–69 s and silent; nothing beyond 100 m is shown visually (long range only as a
bar chart); the demo slide shows screenshots, not the Docker/RViz chain; several slides are dense
with small text; template slide 9 went from 5 cards to 4.

2. §7.2 DELIVERABLES

Docker container: present (the build succeeds, the default command runs the node); weak on one
point: no saved image, only a planned `docker save`. Source code: present. README with launch
instructions: present, but long, with stale statements. Architecture: present (ARCHITECTURE.md).
Algorithm: present (ALGORITHM.md, including limitations). Experiment results: present, strong;
timing on the i7 test stand still owed. Video: present, weak (silent, no narration, no long-range
clip). Demonstration on the control bag: the chain is ready and verified on rebuilt real bags, but
its acceptance checks misfire (findings 2 and 9).

3. FINDINGS

1. web/demo/test_web.py:33 asserts "Best Effort", but resense.rviz:62/90 now say "Reliable";
   `pytest web/demo`: 1 failed; GitHub CI run 72 for fcbb3f8 failed. (Fixed later in fa81206,
   outside the reviewed commit.)
2. scripts/dry_run.sh:89 defaults to `--max-dropped 0`, and README.md:304 and SUBMISSION.md:88
   promise "no frame dropped" — that cannot pass. A dry run with node and player in one container
   reported "dropped 53 … FAIL", 42 of them two 2.1 s holes at start-up. The start-up stall comes
   from the transport, not the CPU, so it will most likely fail on the i7 too (suspected; not
   measured on the i7).
3. README.md:189-190 says `--delay 3` prevents losing the first 1–3 s; in every run the hole was
   still 2.0–3.9 s. EXPERIMENTS.md:838 says the hole is "~1 s" at 120°; measured 2.0–2.7 s on
   roundT_doubleT.
4. The false-alarm results depend on the first processed frame. Feeding exactly the frames the
   node processed into the offline detector reproduces it deterministically: roundT_doubleT an
   extra low-object STOP at 49.7–54.0 m in 4 of 6 start offsets; doubleT_platform 2 STOP frames
   become 10 when starting at frame 20; roundT_pressureGate 0 becomes 1 when starting at frame 35.
   Through ROS roundT_doubleT gave 3, 2 and 1 alarm frames across three runs, one at 54 m, so
   README.md:287-289 and the §3b table ("exactly its 2 known frames, same as offline") depend on
   the run, and `--expect-clear --max-alarm-frames 2` would fail on the run with 3.
5. README.md:186-188 says `--ipc=host` gives shared memory and "without it the clouds may not
   arrive" — stale: the image is UDP-only (Dockerfile:71-72); the comment at docker-compose.yml:32
   is stale the same way.
6. README.md:24 and :65 point the jury to docs/SCORECARD.md "for every criterion"; that file is
   headed v0.6.1 and contains self-scores.
7. SUBMISSION.md:67 row 12 status says "dry run on a real bag pending (28.09)", contradicting the
   same row's text and §3b.
8. Dockerfile:6 refers to a README section "Run with RViz" that does not exist.
9. scripts/console_test.sh:50 checks `--expect-obstacle` on every recording by default; played in
   the documented order (roundT_doubleT, then doubleT_obstacle) it fails: "recording 1: 1 alarm
   frames, expected >= 3" (verified).
10. On obstacle-free roundT_doubleT, CAUTION covers 159–162 of 224–233 frames through ROS, mostly
    from clusters demoted as columns; README.md:76 does not say CAUTION is the normal state, so
    the GO/CAUTION split tells the jury little.
11. detector_node.py:466: on FAULT the node publishes `obstacle_detected=False`; anyone reading
    only that Bool sees "clear" while the path is not monitored (a design concern, from the code).
12. Slide 10 and web/README advertise a live dashboard "через rosbridge", but the image has no
    rosbridge and roslib is loaded from a CDN (web/index.html:104); on an offline stand only replay
    works.
13. Slide 3 (template slide 9): 5 cards reduced to 4, one card and one picture placeholder
    removed and the rest re-centred — a small structural deviation from the template.

4. WHAT WOULD RAISE EACH SCORE MOST (best gain per hour first)

1. (8.6/8.5, ~1 h) Fix findings 2, 3, 5–9: count dropped frames only after the first steady
   frame and relax the dry-run defaults; give console_test.sh arguments for real bags; remove the
   stale SHM, SCORECARD and "pending" text.
2. (8.6, ~1 h) A 10-line jury quick path at the top of the README (build, run, play, echo,
   expected output); state that the first 2–4 s are not processed and what CAUTION normally means.
3. (8.5/8.7, 2–4 h) Make the low-object stage robust to where processing starts (require the bed
   template to warm up for N frames before a low object can cause a STOP, or do not reset on the
   start-up hole); add start offsets (0/10/20/30) to eval_real.py and republish the false-alarm
   numbers under the jury's conditions.
4. (8.6, ~1 h) Ship a `docker save` image with `docker load` instructions.
5. (8.8, 2–3 h) A 2–3 min narrated video: the Docker chain, the hero frame, a synthetic person
   approaching and confirmed at ~148 m; an RViz frame on the demo slide; less text on slides 5,
   13 and 15.
6. (8.7, ~1 h) A one-page decision log (hypothesis → experiment → result → decision) and a "what
   failed" slide taken from the §7 table.
7. (8.5, 2+ h) Look into the start-up stall on the transport side (Fast DDS reliability /
   heartbeat settings, reader history depth) and report the effect.
