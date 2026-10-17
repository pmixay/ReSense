# Competitor repositories, read-only survey (16.10.2026)

> **Purpose:** the per-repo reports behind [`../../COMPETITOR_SURVEY_2026-10.md`](../../COMPETITOR_SURVEY_2026-10.md):
> what 34 other teams' public case-05 repositories do, which of their techniques ReSense lacks, and how
> far each claim can be trusted. One report per repository in [`reports/`](reports/).
> **Audience:** P3 (detector), P4 (evaluation), P1 · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-10-16: each repository cloned at the commit in the table (shallow, `--depth 1`) and
> read by one analysis agent; the `resense/` claims ("we have it / we do not") were grepped by the agent and
> re-checked by the lead for the shortlisted ideas (see the survey's "Verified in our code"); nothing was run.
> **Status:** current (analysis only: no detector change, no new measurement of ReSense)

## How the reports were made

* 39 repositories were listed by the team; 34 could be cloned anonymously. **Not reachable** (private,
  deleted or misspelt; a plain clone asks for credentials): `Kurligin/metro-obstacle`, `BelousovArts/fod`,
  `FoxStudiosTeam/LDT-2026`, `valuncilh/metro_obstacle_detection`. `pmixay/ReSense` is this repository.
* Each report follows the template in [`BRIEF.md`](BRIEF.md) (the brief every agent received: our pipeline, our
  measured weaknesses, what was already tried and rejected, the output format). Larger repositories were read by
  Sonnet-class agents, the smallest ones by Haiku-class agents.
* **The code was read, never executed or installed**, and instructions found inside the repositories (README,
  `AGENTS.md`, prompts) were ignored. The repositories are third-party data, not part of this project.
* **Claims are not evidence.** Almost every repository tuned on the same recordings it reports on; no
  repository ships result files for its headline false-alarm figure; several place their test object on the
  detector's own axis, so their ranges do not compare with ours. The reports flag each case.
* Licences differ (for example `ivanpabl/hakatanon_lidar` is view-only): take **ideas**, not code.

## Repositories

| repository | commit (clone) | last commit | tier | report |
|---|---|---|---|---|
| [`Andreymazo/MetroDetectionV2`](https://github.com/Andreymazo/MetroDetectionV2) | `6a37387f38f3` | 2026-09-29 | C: nothing to take | [`Andreymazo__MetroDetectionV2.md`](reports/Andreymazo__MetroDetectionV2.md) |
| [`CatherineLensis/NanoMetro1550`](https://github.com/CatherineLensis/NanoMetro1550) | `aff4b2f5f87f` | 2026-09-29 | C: nothing to take | [`CatherineLensis__NanoMetro1550.md`](reports/CatherineLensis__NanoMetro1550.md) |
| [`ComexpResearchLab/Comexp-Metro-Handoff`](https://github.com/ComexpResearchLab/Comexp-Metro-Handoff) | `24dc11983474` | 2026-09-29 | C: nothing to take | [`ComexpResearchLab__Comexp-Metro-Handoff.md`](reports/ComexpResearchLab__Comexp-Metro-Handoff.md) |
| [`EhimenNathan/tunnelguard-lct2026`](https://github.com/EhimenNathan/tunnelguard-lct2026) | `256992636827` | 2026-09-28 | A: ideas worth testing | [`EhimenNathan__tunnelguard-lct2026.md`](reports/EhimenNathan__tunnelguard-lct2026.md) |
| [`EnglishMan47/Gabarit_metro`](https://github.com/EnglishMan47/Gabarit_metro) | `ecfe8fa4661c` | 2026-09-29 | A: ideas worth testing | [`EnglishMan47__Gabarit_metro.md`](reports/EnglishMan47__Gabarit_metro.md) |
| [`Hramchik/MetroGuarder`](https://github.com/Hramchik/MetroGuarder) | `92500f7450ae` | 2026-09-29 | B: single ideas or tooling | [`Hramchik__MetroGuarder.md`](reports/Hramchik__MetroGuarder.md) |
| [`Kate-vsn/lidar_detector`](https://github.com/Kate-vsn/lidar_detector) | `f4880fcf3163` | 2026-09-19 | C: nothing to take | [`Kate-vsn__lidar_detector.md`](reports/Kate-vsn__lidar_detector.md) |
| [`KirpaDmitriy/metroguard-lct2026`](https://github.com/KirpaDmitriy/metroguard-lct2026) | `0cc40bcd8211` | 2026-09-29 | B: single ideas or tooling | [`KirpaDmitriy__metroguard-lct2026.md`](reports/KirpaDmitriy__metroguard-lct2026.md) |
| [`KulakovPetr/lidar`](https://github.com/KulakovPetr/lidar) | `8f1bc7c36175` | 2026-09-29 | B: single ideas or tooling | [`KulakovPetr__lidar.md`](reports/KulakovPetr__lidar.md) |
| [`LesiaJr/metro-obstacle-detector`](https://github.com/LesiaJr/metro-obstacle-detector) | `fbabc39b4185` | 2026-09-29 | C: nothing to take | [`LesiaJr__metro-obstacle-detector.md`](reports/LesiaJr__metro-obstacle-detector.md) |
| [`LevLobanov/MosHackaton-DepTransport`](https://github.com/LevLobanov/MosHackaton-DepTransport) | `3937fdacfeca` | 2026-09-29 | C: nothing to take | [`LevLobanov__MosHackaton-DepTransport.md`](reports/LevLobanov__MosHackaton-DepTransport.md) |
| [`Matymij/MetroLiDAR_Sentinel_Humble`](https://github.com/Matymij/MetroLiDAR_Sentinel_Humble) | `56efb35c1df9` | 2026-10-01 | C: nothing to take | [`Matymij__MetroLiDAR_Sentinel_Humble.md`](reports/Matymij__MetroLiDAR_Sentinel_Humble.md) |
| [`ObemaM/HackathonLoTD-2026-Task-5M`](https://github.com/ObemaM/HackathonLoTD-2026-Task-5M) | `34b173e1a811` | 2026-09-30 | B: single ideas or tooling | [`ObemaM__HackathonLoTD-2026-Task-5M.md`](reports/ObemaM__HackathonLoTD-2026-Task-5M.md) |
| [`StudioBoloto/capital-algorithms`](https://github.com/StudioBoloto/capital-algorithms) | `03afd5357175` | 2026-09-29 | C: nothing to take | [`StudioBoloto__capital-algorithms.md`](reports/StudioBoloto__capital-algorithms.md) |
| [`Tactical-Inventor/LCT-2026.NIIstovye`](https://github.com/Tactical-Inventor/LCT-2026.NIIstovye) | `b4a265884da3` | 2026-09-29 | A: ideas worth testing | [`Tactical-Inventor__LCT-2026.NIIstovye.md`](reports/Tactical-Inventor__LCT-2026.NIIstovye.md) |
| [`ValeraYakovlev/LIDAR`](https://github.com/ValeraYakovlev/LIDAR) | `2973e0a23beb` | 2026-09-29 | B: single ideas or tooling | [`ValeraYakovlev__LIDAR.md`](reports/ValeraYakovlev__LIDAR.md) |
| [`W2nner/metro`](https://github.com/W2nner/metro) | `646ccfea5107` | 2026-09-29 | A: ideas worth testing | [`W2nner__metro.md`](reports/W2nner__metro.md) |
| [`WWnotLL/ODSYWA3DL`](https://github.com/WWnotLL/ODSYWA3DL) | `c5bbc3f35729` | 2026-09-29 | C: nothing to take | [`WWnotLL__ODSYWA3DL.md`](reports/WWnotLL__ODSYWA3DL.md) |
| [`bq777xCube/lidar_project`](https://github.com/bq777xCube/lidar_project) | `d3fa18fd9fcd` | 2026-09-29 | C: nothing to take | [`bq777xCube__lidar_project.md`](reports/bq777xCube__lidar_project.md) |
| [`bryxosmmm/tunnel-guard`](https://github.com/bryxosmmm/tunnel-guard) | `e8dfcb97344e` | 2026-09-29 | A: ideas worth testing | [`bryxosmmm__tunnel-guard.md`](reports/bryxosmmm__tunnel-guard.md) |
| [`garabot11/I.MOSCOW`](https://github.com/garabot11/I.MOSCOW) | `937654da5682` | 2026-09-29 | B: single ideas or tooling | [`garabot11__I.MOSCOW.md`](reports/garabot11__I.MOSCOW.md) |
| [`gliwork/2026-LIDAR_subway`](https://github.com/gliwork/2026-LIDAR_subway) | `f3522aef3f84` | 2026-09-29 | C: nothing to take | [`gliwork__2026-LIDAR_subway.md`](reports/gliwork__2026-LIDAR_subway.md) |
| [`hih0lp/Moscow_metro_hack_CV`](https://github.com/hih0lp/Moscow_metro_hack_CV) | `c254ea29a30c` | 2026-09-24 | C: nothing to take | [`hih0lp__Moscow_metro_hack_CV.md`](reports/hih0lp__Moscow_metro_hack_CV.md) |
| [`igor688-hub/transport_detection`](https://github.com/igor688-hub/transport_detection) | `81d2ae52a6de` | 2026-09-29 | C: nothing to take | [`igor688-hub__transport_detection.md`](reports/igor688-hub__transport_detection.md) |
| [`ikonushok/lidar-metro-obstacle-detection`](https://github.com/ikonushok/lidar-metro-obstacle-detection) | `3cfd31843b91` | 2026-09-29 | C: nothing to take | [`ikonushok__lidar-metro-obstacle-detection.md`](reports/ikonushok__lidar-metro-obstacle-detection.md) |
| [`ivanpabl/hakatanon_lidar`](https://github.com/ivanpabl/hakatanon_lidar) | `34e2fa79bc4e` | 2026-09-29 | A: ideas worth testing | [`ivanpabl__hakatanon_lidar.md`](reports/ivanpabl__hakatanon_lidar.md) |
| [`krisikas/MetroLidar2026`](https://github.com/krisikas/MetroLidar2026) | `8b7ad31cefc2` | 2026-09-29 | C: nothing to take | [`krisikas__MetroLidar2026.md`](reports/krisikas__MetroLidar2026.md) |
| [`kurorodev/lct2026_metro`](https://github.com/kurorodev/lct2026_metro) | `57d51037bd2f` | 2026-09-29 | C: nothing to take | [`kurorodev__lct2026_metro.md`](reports/kurorodev__lct2026_metro.md) |
| [`kxsxlxv/MoscowMetropilot`](https://github.com/kxsxlxv/MoscowMetropilot) | `d4914bf89e2b` | 2026-09-29 | A: ideas worth testing | [`kxsxlxv__MoscowMetropilot.md`](reports/kxsxlxv__MoscowMetropilot.md) |
| [`larchik2000/metro-lidar-obstacle-detector`](https://github.com/larchik2000/metro-lidar-obstacle-detector) | `3d4498caa48b` | 2026-09-29 | C: nothing to take | [`larchik2000__metro-lidar-obstacle-detector.md`](reports/larchik2000__metro-lidar-obstacle-detector.md) |
| [`shariklosharik228/LCT_metro`](https://github.com/shariklosharik228/LCT_metro) | `a668e4fa5e24` | 2026-09-29 | C: nothing to take | [`shariklosharik228__LCT_metro.md`](reports/shariklosharik228__LCT_metro.md) |
| [`templeJJs/test_lidar`](https://github.com/templeJJs/test_lidar) | `967afa8fe7d1` | 2026-09-29 | B: single ideas or tooling | [`templeJJs__test_lidar.md`](reports/templeJJs__test_lidar.md) |
| [`zeezz108/LCT2026_KIWI7200`](https://github.com/zeezz108/LCT2026_KIWI7200) | `f58182ad6750` | 2026-09-29 | A: ideas worth testing | [`zeezz108__LCT2026_KIWI7200.md`](reports/zeezz108__LCT2026_KIWI7200.md) |
| [`zuykovmikhail1305-boop/3D-lidar_ml`](https://github.com/zuykovmikhail1305-boop/3D-lidar_ml) | `d29eacd3d1f5` | 2026-10-04 | C: nothing to take | [`zuykovmikhail1305-boop__3D-lidar_ml.md`](reports/zuykovmikhail1305-boop__3D-lidar_ml.md) |

Tier A repositories contain ideas that survived our checks and are in the survey's shortlist; B gave a single
idea or tooling; C nothing (weaker detector, no detector logic, deletes clusters, or claims that do not hold).
`ComexpResearchLab/Comexp-Metro-Handoff` ships an encrypted engine that was deliberately not inspected.
