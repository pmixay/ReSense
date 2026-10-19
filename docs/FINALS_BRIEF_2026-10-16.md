# Experts' message to the finalists (16.10): criteria, new data, launch requests, and what we have

> **Purpose:** the experts' general message to the finalists, verbatim, set against the shipped system: for each of
> the nine criteria and each new request, what exists (with the code line), what is missing, and the work it adds
> to [`BACKLOG.md`](BACKLOG.md) (cards N1–N4, same format).
> **Audience:** P1 (to distribute), P2 (RViz, visuals), P3, P4 · **Owner:** P1 · **Language:** EN, the message in RU
> **Last verified:** 2026-10-16 against `main` (`3fdc879`, detector = `v1.0.0`): the code facts (marker code,
> player script, calibration, node input handling) read by the lead in the source; the numbers from
> [`evidence/axis_profile_2026-10-16/`](evidence/axis_profile_2026-10-16/README.md) and the
> [13.10 judgement](evidence/judgement_2026-10-13/README.md). Nothing was run in Docker for this note.
> **Status:** the message and the 16.10 analysis are kept as written; the state of each criterion and card on
> 19.10 (N1, N4 done locally; N2 measured; N3 failing, in work; gauge stability and curves in work) is in
> [`BACKLOG.md`](BACKLOG.md) §9b

## 1. The message (verbatim, as relayed by the team)

> Общее сообщение от экспертов финалистам
>
> «Основные критерии оценки:
> 1. Дальность детекции (как далеко случается первый детект препятствия);
> 2. Дальность габарита (как далеко простраивается габарит);
> 3. Устойчивость габарита (бокс габарита не моргает, не исчезает, не уходит с путей);
> 4. Отсутствие ложноположительных срабатываний;
> 5. Отсутствие ложноотрицательных срабатываний;
> 6. Работа алгоритма в реальном времени (частота 10 Гц);
> 7. Работа фильтра;
> 8. Дополнительные фичи;
> 9. Удобство запуска.
>
> Напомним, что нами будет расширен датасет: будет выдана дополнительная синтетика со схожими лидарными облаками и
> дополнительными препятствиями (в т.ч. человек и симуляция пыли/взвеси) и реальная запись с другого лидара для
> дополнительной оценки. Уточним, что нужно учесть отличия в направлении осей на другом лидаре.
>
> Отметим дополнительные запросы по упрощению запуска:
> - Запуск docker container с графикой;
> - Наличие rviz в докер контейнере;
> - Возможность останавливать/замедлять бэги (функционал есть во встроенном проигрывателе ros2 bag play, он должен
>   быть доступен при запуске контейнера, из консоли);
> - Возможность быстро переключать разные бэги (желательно без перезапуска контейнера).»

Together with the live Q&A of the same day ([`organizers/answers.md`](organizers/answers.md) §10): a false positive
counts the same as a miss, 300 m is the ideal range, the check mixes real and synthetic data, and the team's own
project needs "a more stable gauge and the gauge synchronised with turns (it does not match well)".

**What is new against [`BACKLOG.md`](BACKLOG.md):** it is organised by ТЗ §8 (eight criteria, the judge's weights).
The experts' list is different: it names the **gauge** twice (range, stability) as criteria of their own, and adds
dust, a second lidar and four launch requests. The backlog covers the axis (K1, K2), false alarms (F1, F2), range
(R1–R3), CAUTION (C1), the player's start-up (S1) and speed (S2, S5); it does not cover the gauge as a displayed
object, dust, the second lidar, or the interactive launch.

## 2. The nine criteria against the shipped system

| # | criterion | what exists | gap | where |
|---|---|---|---|---|
| 1 | detection range (first detect) | judge: person-size box ~220 m and 1 m box ~150 m on straight track, 41–75 m on curves and double track, 0.3 m objects from ~45–56 m | curves, double track, small objects; a 0.3 m cube has 1–2 returns beyond 80 m, so only large objects can reach 300 m | K2, R1, R2; [axis profile](evidence/axis_profile_2026-10-16/README.md) |
| 2 | gauge range (how far the gauge is built) | `axis_valid` (last observed boundary bin + 15 m, +50 m straight) is in the status JSON (`track.axis_valid`), `clear_distance` is a topic; RViz draws the gauge to `marker_x_max` = 250 m (`detector_node.py:1268`, `launch/detector.launch.py:35`) **whatever `axis_valid` is** | the drawn range is not the trusted range; beyond ~120 m the drawn edges can be off the rails (axis error 90th percentile 1.55 m at 120–150 m, 3.3 m at 150–200 m, against a 1.05 m half-width) | **N1**, K2 |
| 3 | gauge stability (the box does not blink, vanish or leave the track) | the markers are cleared and rebuilt every frame (`DELETEALL` + `ADD`, `make_markers`, `detector_node.py:1239-1307`) from that frame's live track; the corridor is **two lines** at rail head + 1 m, not a box (no top, no height); grey only when freshness is invalid | no hysteresis or hold on the displayed gauge; the raw per-frame axis moves 0.05–0.11 m per frame beyond 100 m (90th percentile 0.29–0.38 m beyond 120 m); the live axis smoothing is per time, not per distance (K1) | **N1**, K1 |
| 4 | no false positives | judge: ~91 false `STOP` episodes per hour of empty tunnel, ~2.5 per km on the ride; CAUTION on 43 % of empty frames | the experts count a false positive like a miss | F1, F2, C1; [survey](COMPETITOR_SURVEY_2026-10.md) |
| 5 | no false negatives | all 8 in-gauge organizer objects and the real person reach `STOP` | judge's silent misses: tall narrow objects demoted as `column`, objects merged with edge structure on curves; small objects late | H1, H2, R1, R2 |
| 6 | real time at 10 Hz | 120° real-time with margin; 360° p95 106–119 ms on 4 vCPU | 360° at the frame period; the literal `ros2 bag play <bag>` gives stale results | S1, S2, S5 |
| 7 | "filter" ("Работа фильтра") | not defined in the message | unclear whether it means the track filter (confirmation and persistence), the false-alarm filtering, or a dust filter | question to the organizers ([`QUESTIONS.md`](QUESTIONS.md)) |
| 8 | extra features | RViz layout, Foxglove bridge, web dashboard, web prototype (PR #31), `clear_distance`, health status, offline CLI, synthetic generators | none needed beyond N1 | PT1 |
| 9 | ease of launch | one command for the jury (`scripts/play_bag.sh`), `docker load` + `docker run` in ~3 s, topics auto-discovered | see section 3 | E1, E2, S1, **N4** |

## 3. New requests against the code

| request | state | gap |
|---|---|---|
| Docker container with graphics | documented: `xhost +local:docker && docker run --rm -it --net=host --ipc=host -e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix resense ros2 launch resense_ros detector.launch.py rviz:=true freshness_mode:=replay` (`README.md`), `scripts/run_demo.sh` | one documented path; no software-rendering fallback for a machine without GPU passthrough; not part of the CI acceptance |
| RViz in the container | `ros-humble-rviz2` is in the image (`docker/Dockerfile:32`), the layout is `ros2_ws/src/resense_ros/rviz/resense.rviz`, `rviz:=true` starts it | what RViz shows of the gauge is weak (criteria 2–3): N1 |
| pause or slow a bag from the console | `ros2 bag play` and its keyboard controls are in the image; **`scripts/play_bag.sh` runs the player with `--disable-keyboard-controls` and no TTY** (`scripts/play_bag.sh:113`), so the one-command path cannot pause or slow; the README's manual route (step 3, a console with ROS 2) can, but does not say so | an interactive path through the image and the script, documented: **N4** |
| switch bags quickly, without restarting the container | the node restarts its detector by itself on a topic or `frame_id` change, a header-stamp jump of more than 30 s forward or 0.5 s back, and keeps discovering topics while silent (`detector_node.py:690-705`, `test_pause_resume_timestamp_jumps_input_switch_and_recovery`) | not stated for the jury; no helper that plays several bags in a row against one running node; **N4** |
| another lidar: different axis directions | `sensor_forward / left / up` and `auto_calibrate`: the orientation is searched among the 8 proper rotations that keep the configured up axis vertical (all 24 with `keep_up_axis: false`), adopted only after `orientation_votes` agreeing frames and only if the configured mapping failed its sanity check; a sensor mounted on its side must be described by the parameters (`resense/calibration.py` module docstring) | the first frames before adoption; a missing `ring` field (read as 0, `resense/pointcloud.py:82`) and other channel geometry are not exercised; the far multi-ring rules assume 128 elevation channels; nothing was tested on a second lidar: **N2** |
| dust / suspension in the synthetic data | no dust model anywhere in `resense/` (the only mention is a `health.py` docstring: "fog" shortens the sight line); persistence (3 frames over 0.5 s) and voxel-count bars would filter some of it, unmeasured | **N3** |

## 4. Cards

Format and roles as in [`BACKLOG.md`](BACKLOG.md) §1. N1 and N4 are node, launch and visualisation lanes (no
detector seal); N2 and N3 are measurements first and become detector items only if they find a problem.

#### N1 · The gauge as a stable, honest box in RViz (criteria 2 and 3)
**Owner** P2 (markers) with P1 (node) · **Mode** A · **Size** M · **Depends on** K1 for the live-axis smoothing;
no seal for the display change
* **Evidence:** `make_markers` draws two `LINE_STRIP` edges at rail head + 1 m for the whole `marker_x_max` = 250 m,
  clears everything each frame, and draws the same line whether the axis is supported or extrapolated. The axis profile
  shows the extrapolated part is off the track in a tenth of the frames beyond 120 m and by metres beyond 150 m.
* **Tasks:** (1) draw the gauge as a **box outline** (2.1 m wide, 0.12–3.0 m above the rail head, per
  `gauge.profile`) along the fitted axis; (2) its length is the **trusted range** (`axis_valid` / `clear_distance`),
  drawn solid, with a visibly different style (dashed or translucent) beyond it up to the extrapolation limit, or not
  at all; (3) smooth and hold the **displayed** edges only (weight per travelled distance as in K1, hold the last good
  edges a few frames when the fit is lost, never grow the range in one frame); the decision path is untouched;
  (4) publish the drawn range and a "gauge valid" flag in the status JSON so the web view and the judges' scripts read the
  same number; (5) a replay check of the drawn edges on `doubleT_obstacle` and a curve recording.
* **Done when (proposed):** on `cloud_with_fake_obj`, the displayed edge's frame-to-frame lateral change at 40 / 80 /
  120 m has a 90th percentile ≤ 0.05 / 0.08 / 0.15 m (the raw fit: 0.07 / 0.09 / 0.29 m); no frame in which the
  box disappears while the node is `GO` or `STOP`; the drawn solid length never exceeds `axis_valid`; the status
  JSON carries the range; a screenshot of the box on a curve goes into the deck (PT1).

#### N2 · Second lidar: axis directions, channels, fields (new real recording)
**Owner** P3 + P4 · **Mode** A · **Size** M · **Depends on** X3 (battery), the organizers' metadata
* **Evidence:** section 3. Nothing is tested on a lidar other than the Hesai Pandar128 the data come from.
* **Tasks:** (1) an **orientation battery**: rotate `doubleT_obstacle` and a ride chunk through all 8 (and the 24)
  axis permutations and upside-down mounts with `auto_calibrate` on; record the frames until adoption and what the node
  reports meanwhile (it must not be a silent `GO`: `FAULT` or `CAUTION`), and that the decisions after adoption equal the
  unrotated run; (2) **field variants:** no `ring`, every second channel dropped, other elevation spacing, intensity on
  0–1 and 0–255, `float` and `u1` types, a different `frame_id` and topic; (3) write the second-lidar launch
  parameters (`sensor_forward / left / up`, `keep_up_axis`) and the "sideways mount" limit into the jury README with an
  example; (4) ask the organizers for the model, field layout, FOV, channel count and axis convention of the new
  recording before they hand it out ([`QUESTIONS.md`](QUESTIONS.md)).
* **Done when:** all 8 upright / inverted permutations adopt within the calibration's frame budget with decisions equal
  to the baseline on `doubleT_obstacle` (193 `STOP`); every field variant either gives the baseline decisions or a
  reported degradation; the README shows the command for a lidar whose axes differ.

#### N3 · Dust / suspension (the organizers' synthetic dust)
**Owner** P4 (generator, measurement) + P3 · **Mode** A · **Size** M
* **Evidence:** section 3, no dust model and no dust measurement.
* **Tasks:** (1) a generator in the style of `resense/synthetic.py`: random returns in a volume ahead of the sensor
  (density per m³, low intensity, a distance profile, and the loss of far real returns behind a dense cloud), at three
  densities; (2) on the set F / O backgrounds and the empty recordings: false `STOP` and `CAUTION` per density, and the
  first `STOP` of a real person and of the organizers' objects against the clean run; (3) only if (2) finds a problem,
  candidates in order of safety: a larger voxel-count bar for isolated low-intensity returns, a dust flag in the
  health status instead of an alarm, never a delete; (4) say what the node reports under heavy dust (degraded, not
  silent `GO`).
* **Done when (proposed):** false `STOP` episodes per dust density ≤ the clean run + 1 on the five empty recordings;
  the real person's first `STOP` within 10 % of the clean distance at the lowest density and reported as degraded at the
  highest.

#### N4 · Interactive launch: pause, slow, switch bags, graphics
**Owner** P1 · **Mode** A · **Size** M · **Depends on** S1 / E2 (the same files); no seal
* **Evidence:** section 3: `play_bag.sh` disables the keyboard controls and has no TTY; nothing documents pausing,
  slowing or queuing bags; switching works in the node but is not stated or scripted.
* **Tasks:** (1) `scripts/play_bag.sh --interactive`: the player in `docker run -it` with the keyboard controls on and
  `--rate` passed through, the node unchanged, the decision listener still printing; keep the non-interactive default
  for the stand; (2) accept **several bag directories** in one call, played one after another against **one** running
  node, printing each bag's decision changes (the node resets itself between them); (3) document in the jury README and
  `gitbook/getting-started/run-on-a-bag.md`: the player's own controls and `--rate`, a second console in the running
  container, and that bags can be switched without a restart (the conditions: another topic, `frame_id`, or stamps
  jumping by > 30 s forward or 0.5 s back); (4) graphics: one documented command and a software-rendering fallback
  (`LIBGL_ALWAYS_SOFTWARE=1`) for a machine without GPU passthrough, checked on a clean host with X11; (5) a CI step
  that plays two synthetic bags in a row through one container (the unit test exists, the container chain does not).
* **Done when:** from a fresh `docker run`, pause, resume and `--rate 0.5` work from the console; a second bag after the
  first gives a restarted detector with correct decisions and no container restart; RViz opens from the documented
  command; the new CI step is green.

## 5. Suggested order

N4 and N1 first (small, visible to the experts, no seal); then N2's battery (it needs no new data) and the
organizers' answers; N3 once the generator exists and the organizers' dust sample arrives. The detector-side work
stays as in [`BACKLOG.md`](BACKLOG.md) §4, with the [survey's](COMPETITOR_SURVEY_2026-10.md) shortlist attached to K2,
F2 and H2.
