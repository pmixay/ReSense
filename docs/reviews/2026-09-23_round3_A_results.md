# Independent review, round 3: results (8.1–8.4) — commit `fcbb3f8`, 23.09

The report of the reviewer who judged criteria 8.1–8.4 of the technical specification (content
unchanged, lightly reformatted).
The reviewer had no stake in the work, was told to distrust the team's claims, did not modify the
repository and re-ran the evaluations on the frame cache. How each finding was checked and what
was done about it: [`../SCORECARD.md`](../SCORECARD.md).

---

1. SCORES

8.1 Works — 6/10. Finds the one real scene well; frequent false STOPs and bed-level misses.
Verified (own scorer score.py/ride.py on runs/sw_lowW22): real person 58/61 envelope frames, first
STOP frame 11 (0.3 s after entry), distance error ≤0.23 m; object-on-rail own detection 121/185,
STOP in 124/132 frames after the person leaves; five empty bags 81 alarm frames/20 events; ride
164/47 (3.6/km). Held down by: ride has 52 STOP onsets (28 separate episodes when gaps ≤1 s are
merged) — a false STOP roughly every 43 s; nothing on the bed between the rails is reported by
policy (team's set F: 0.5 m box 1/6, dog-sized 1/6, 30 cm cube 1/6, 30×30×10 0/6) though the
organizers explicitly named "a dog thrown on the track"; a 3 cm hanging cable 74 % of frames at
0–50 m, 3/6 at the envelope edge; decision flickers (no hold-over).

8.2 Range — 6/10. Person reliably held from ~115–135 m on straight track; small objects only
<50 m. Verified by re-running the straight set F (bit-exact match): person first hit median
148 m, ≥90 % sustained 135 m, every-10 m-band 115 m; crate 95 m, trolley 70 m (band). No return
beyond 209–210 m in sampled frames. Held down: per-sequence band ranges for the person spread
20–160 m; cable band ~20 m (sustained 53 m, 4/6); rail-head small objects 42–47 m; curves
58–86 m (with placement on the detector's own axis, finding 5); 14 of the 47 ride false-alarm
events are first seen beyond 100 m (the far-field rule's cost).

8.3 Speed — 6/10. CPU-only, ~1 core, 186 MB; real time at 120°, at the edge at 360°. Verified on
the (shared 4-vCPU) sandbox with bench_node_path + CPU-time variant: 120° 66–70 ms mean / p95
76–80; 360° 94–96 ms mean / p95 106–121. Held down by stale headline timing (finding 2), 86/201
frames dropped at 360° in the Docker dry run (6.8–8.3 fps, docs/evidence obstacle_node.log),
0.5 s confirmation for objects that appear already inside the envelope, a scene reset after any
input hole > 1 s, no i7-9700E measurement.

8.4 Generalisation — 6/10. Sound approach, but thresholds tuned on every frame they are scored
on. No map, per-frame tunnel model, data-driven mount calibration; v0.5 was frozen before the
ride existed and alarmed on 3.2 % of ride frames vs 4.2 % on its tuning bags (EXPERIMENTS §1c) —
the only real out-of-sample result. v0.6.2 has fewer events than v0.6.1 in 12/13 subsets
(consistency_check.py, verified). Held down: ~15 hand-tuned rules, no held-out obstacle data;
the straddle thresholds sit on the one real object (0.10 → 0.12 m loses 25 % of its frames);
the bed-level policy is at odds with the organizers' synthetic generator, whose placement is
unknown; synthetic placement is circular (finding 5).

2. FINDINGS

1. README.md:47–48 "held from 115 m inward" is the median of 6 sequences; per-sequence values
   are 80, 110, 140, 160, 20, 120 m. The same line's "a 3 cm hanging cable at 95 m" is a single
   first-frame hit (band median ~20 m). VERIFIED (my re-run + bands.py).
2. README.md:57–58 "42–58 ms mean, p95 52–69" are v0.6 figures. Interleaved A/B on the same
   machine: doubleT_obstacle v0.6 (236ae53) 55–57 ms vs HEAD 73–77 ms (+33 %); roundT_doubleT
   42.2 vs 52.9 ms (+25 %). VERIFIED (`resense.cli bench` on git-archive trees).
3. resense/calibration.py:292 observe_mount runs on every frame until the calibration freezes
   (~200 frames), +10–15 ms per frame for the first 20 s of every recording — the whole length of
   a 20 s control bag. HEAD: 53 ms mean before freezing, 42 ms after; v0.6: 38 ms throughout.
   Bisected to 8689bf6. VERIFIED by timing; the cause read from the code.
4. EXPERIMENTS.md:616–617 blames the ~20 m sustained-range collapse on "the near-range bed fit".
   The real cause is a 3.4 s hole in the recording (new_data_169_0014 → 0015): the object jumps
   ~65 m, the scene resets, and the object is a gauge candidate with 200–268 points at 30–24 m but
   unconfirmed for 4 frames. VERIFIED (diag168.py).
5. scripts/far_range_eval.py:120–131 + resense/synthetic.py:162–163 place the object at
   `track.center_y` of the detector's own model, so axis errors never move it out of the corridor,
   flattering the curve and edge sets. SUSPECTED effect size; the placement itself is VERIFIED
   from the code.
6. Bed depth is stated as 0.44 m "(track.rail_offset)" (EXPERIMENTS.md:627) and 0.44–0.6 m
   (ALGORITHM.md:553); the stored runs have rail_offset medians of 0.32–0.37 m per recording; the
   injector default is 0.25 m; EXPERIMENTS.md:664 says 0.3–0.4 m. VERIFIED.
7. ALGORITHM.md:296 gives the object top as 0.10–0.15 m (median 0.13); the labels give a median
   of 0.17 m (0.07–0.22 after frame 68). VERIFIED.
8. README.md:50–51 quotes "crate at 182 m" with train speed; with speed the crate's sustained
   range falls 117 → 89 m and person recall at 50–100 m 94 → 83 %. VERIFIED from the stored JSON.
9. README.md:62 "8–10 fps steady" at 360°; the dry-run log shows 6.8–8.3 fps. VERIFIED.
10. The decision flickers ("matched in the current frame", ALGORITHM §4): 8 non-STOP frames among
    132 with the object present; squareT_platform has 33 STOP onsets for 15 events. VERIFIED.
11. Confirmed as stated: 81/20 and 164/47; 58/61, first STOP frame 11; 121/185 and 118/126;
    196 frames (1.4 %) with health warnings; decisions identical between v062d and sw_lowW22 on
    all 13 759 frames (the refactor and the width cap changed nothing).

3. WHAT WOULD RAISE THE SCORES (best gain per hour first)

1. 8.3, ~1 h: call observe_mount only every obs_spacing frames after the provisional phase;
   re-time on the current code and replace the README headline.
2. 8.1, ~1 h + one eval_real run: keep a confirmed gauge track alarming through 1–2 missed frames
   (removes the flicker); report STOP episodes next to track events.
3. 8.2/8.4 credibility, ~30 min: "median of 6" and the per-sequence ranges in the README; correct
   finding 4 and flag sequences that cross recording holes; headline the sustained / band ranges,
   not first hits.
4. 8.4/8.2, 2–3 h: re-run the curve and edge sets of set F with independent placement (e.g.
   anchored on the axis estimated once the train is within ~30 m).
5. 8.1/8.4, 3–4 h: an opt-in near-range bed-object rule (≥ 0.3 m wide and tall, within 30 m);
   sweep its false-alarm cost on the ride — the dog / 0.5 m box case is the largest detection gap.
6. 8.3, ~2 h: about half of each 360° frame lies within 4 m of the sensor; measure whether
   cropping it before the track stage is safe — it could cut the 360° cost substantially.
7. 8.1/8.2, ~a day: a lining-anchored far height reference to remove the false alarms beyond
   100 m.
