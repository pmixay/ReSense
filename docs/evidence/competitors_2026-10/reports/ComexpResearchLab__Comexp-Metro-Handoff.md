# ComexpResearchLab/Comexp-Metro-Handoff

## Verdict
Detection logic is not inspectable: `ros/engine.enc` is an encrypted, machine-bound engine, and I did not attempt to decrypt or bypass it. Readable parts are the ROS wrapper, docs and tools. Claims (no false alarms on >1200 empty frames, 13/13 organiser objects, 100-130 m range) come with no artifacts, so they are unverifiable.

## Pipeline (as documented; code not readable)
1. `ros/metro_detector/metro_detector/cloud.py`: PointCloud2 decode via numpy structured dtype; if the cloud is not in the Hesai OT128 driver grid (no ring field, or not 128 x k points), rebuild the grid from beam geometry (`regrid`, L99-140, table `sensor_hesai128.npz`).
2. `docs/algorithm.md` section 1: odometry by point-to-plane ICP (proprietary variant) between frames, with speed captured only after several agreeing frames, timestamp-based stepping over missed frames.
3. Section 2-3: rails and track axis (also on curves), tunnel section model (round, rectangular, station), with infrastructure explained by walls and vault.
4. Section 4: 2.1 x 3 m corridor along the axis, forward to the horizon.
5. Section 5: objects inside the corridor clustered, tracked in odometry longitudinal coordinates, world-referenced.
6. Section 6: alert only after several consecutive frames; alerts suppressed during odometry warm-up (about 2 frames median).
7. `node.py`: one tracker per input topic, bounded drop-oldest queues (`take`, `prep`, `bound`, `worker`, L182-236), QoS depth 100 reliable by default (L93, L121).

## Candidate ideas (table)
| # | idea | where in code | mechanism (1-2 lines) | have in ReSense? (yes/partial/no, evidence) | expected effect: recall / range / FPR | cost & risk | evidence in repo (measured? held-out?) |
|---|---|---|---|---|---|---|---|
| 1 | Sensor-grid rebuild for clouds without the driver's ring field: match each return to a beam by elevation table and azimuth firing phase, dual-return column layout | `ros/metro_detector/metro_detector/cloud.py:regrid` (L99-140), `_ph`, `_table`, `regrid_cols` (L139+) | Recovers ring and column from unordered XYZ so per-ring rules (cross-ring evidence, ring counts) run on any bag | partial: ReSense decodes ring from elevation angle (`resense/farrails.py` L16) and treats unknown ring as None (`resense/detector.py` L116, L406). No azimuth-phase or dual-return column rebuild found (grep `regrid|firing|phase`) | no direct recall change; enables ring-based evidence on organiser bags | moderate; assumes the Hesai dual-return firing pattern | Not measured in repo docs. Byte-identical Rust/Python regrid is claimed in code comments |
| 2 | Speed-capture gate: accept an odometry speed only after N consecutive agreeing frames, then reject jumps; suppress alerts until it is captured | `docs/algorithm.md` sections 1 and 6 (engine internals not readable) | Stops a wrong early speed from shifting the corridor or accumulation | partial: ReSense has `egomotion.py` with a confidence and `ego_veto` (`resense/config.py` L357-362), and `axis_warmup_frames` (`config.py` L105). The explicit consecutive-agreement gate is not found | fewer early false alarms; the gain would be in accumulation at 40+ m | low | Stated only in the docs; no numbers |
| 3 | Object tracking in an odometry-anchored longitudinal coordinate (static objects keep a fixed s, so association is a 1D match) | `docs/algorithm.md` section 5 (engine internal) | Simplifies association and makes the static-object test exact when odometry is good | partial: ReSense tracks in sensor distance with approach-line fits and ego-compensated accumulation (`resense/accumulate.py`, `tracking.py` `approach_*`). The same idea, applied to association, is not found | confirmation stability on long tracks | medium; a wrong odometry offset breaks every track at once | Not measured |
| 4 | Timestamp-based odometry that steps over dropped frames (distance per elapsed time, not per message), and a full re-warm-up after long gaps | `docs/algorithm.md` section 1 | Keeps speed continuous through replay or bus drops | yes: `rates_per_period` counts nominal frame periods from stamp intervals (`resense/config.py` L106); `frame_dt` in tracking | — | — | — |
| 5 | Synthetic insertion in moving records with occlusion and a sensor noise model, so range is measured on a moving train | `docs/algorithm.md` "Синтетические препятствия" | Realistic first-detection range on the real ride | yes: `resense/synthetic.py` (BEAM_DIVERGENCE_RAD, catalogue sizes, approach sequences `cli.py` `--sequence`) | — | — | — |
| 6 | Replay parity harness: compare node per-frame records with the offline engine run, matching by (topic, stamp), with integer fields exact and floats within a tolerance, and a note that libm differences force the tolerance (`ros/tools/compare_alerts.py`) | `ros/tools/compare_alerts.py`, `node_sim.py`, `live_check.sh` | Proves that the deployed node and the offline run agree frame by frame | partial: ReSense has candidate-parity checks on semantic outputs (`scripts/analyze_quality_candidates.py --require-parity`) but no ROS-vs-offline per-frame comparer found | — | low | Tool present; no run results in repo |

## Things done worse than ReSense / red flags
- Not inspectable: the rules, thresholds and ICP odometry are withheld by design, and the machine-bound engine blocks offline re-runs on other hardware, so no claim can be reproduced here.
- Unbacked headline numbers: no per-chunk table, no held-out statement, no eval artifact; the demo videos sit on an external URL.
- Timing claims come from different hardware (local rig 68-80 ms, consumer 8-core 80-160 ms, target i7-9700E 'faster per core' with no number).
- Drop-oldest queues (`node.py` L182-222) keep latency bounded but change the frame count of the record, so counts depend on replay QoS.

## Eval/data tooling worth borrowing
- `ros/tools/qos_replay.yaml`: a deep reliable replay queue (depth 200) so an offline `ros2 bag play` loses no frames. The README reports a 3-5 % loss without it. Use it for any ROS replay that scores per-frame.
- `ros/tools/compare_alerts.py`: a per-frame, per-object comparer between node output and reference run, with an explicit float tolerance and a statement of why (libm). A good pattern for regression between the ROS node and the offline tool.
- `ros/tools/engine_bench.py` and `node_sim.py`: latency and node simulation harnesses, useful for the 10 Hz budget check.
