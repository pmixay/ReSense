# H1: реальные wrong-selected-pair и no-rail limits

> Компактная публикация: raw JSON/NPZ, исходники и логи находятся в
> `raw-evidence.tar.xz`. Exact allowlist, проверка хешей и восстановление
> исходных filenames для reviewer scripts — [PUBLICATION.md](PUBLICATION.md).

**Найдены воспроизводимые false collision core/STOP и misses на неизменённом
full detector.** В физических синтетических сценах estimator действительно
выбирает отвлекающую пару при видимой правильной host-паре. Raw-rail anchor
подтверждает согласованность выбранной пары, но не её семантику «путь поезда».
Это условный synthetic counterexample, не оценка частоты на реальных путях.

Измеренный checkout: repo `/home/aiops/resense`, HEAD
`f56ad5e62d9d051811c804734c7731b6951eae90`. Изменения только в этом новом evidence
directory и `/tmp/opencode/h1-rail-limits`. Production/configuration/index/HEAD
сверены до/после. Freeze R3: 40 файлов, digest
`6d091081769104657ecc2c0b06f53049647d4f6c7327b7429bbda92673782452`, verify PASS.

## Протокол и oracle

[PROTOCOL.md](PROTOCOL.md) записан до первого эксперимента;
[ACCEPTANCE_PLAN.md](ACCEPTANCE_PLAN.md) фиксирует directed matrix после
exploratory forcing. Успешность evidence не означает detection PASS.
Исторические 72 `ambiguous_pair` не используются как wrong-pair tests.
Новые forcing screens сохранены полностью, включая неудачные попытки.

Независимый caster `h1_cast.py` пересекает исходные лучи Pandar с bed, стенами,
потолком, колонной и rail-like AABB; сохраняется только ближайшая поверхность.
Host задан геометрией: center **0**, головы **Y=±0.795 м**. Distractor centers
**±0.4/±0.6 м**, та же ширина пары 1.59 м. Для обнаруженных failures host-rise
над bed **0.20 м**, distractor-rise **0.30 м**; ширина ridge **0.08 м**.
Это прямоугольные rail-like surrogate ridges, не точный профиль рельса.
Параллельные близкие пары моделируют неоднозначную геометрию/элементы перевода;
семантика host — явно заданная истина fixture, detector её не получает.

Истинный host head здесь **Z=-1.98 м** (`bed + host_height`), а не -1.83 м.
Независимый envelope: **|Y|≤1.05 м, h=0.12..3.0 м от истинного host head**.
Колонна 0.46×0.46 м, top 3.22 м в исходной fixture-системе; base Z=-1.83 м,
то есть 0.15 м над head этих lower-host scenes. Геометрия при изменении rise
не переименовывается в стандартный fixture. Для стандартного host-rise
0.35 м head Z=-1.83 м.

Оба исходных known-fixture casts (rails off/on) совпали **побайтно по XYZ и
ring**, target count 84. Rail-free case45 SHA-256
`680878ed4f0b233cec517f999ca8648b1193522c929b7ce0f9df9fad7d545a20`.
Метки caster: 1 target, 10/11 host, 20/21 distractor, 2 blocker, 0 room.
В component fixture номера rails другие; их массивы отдельно сверены с fixture.

## Full detector: конкретные failures

Во всех строках ниже default `DetectorConfig`, fresh `Detector`, **14 сканов**
одинакового статического raw ray-cast с шагом timestamp 0.1 s; supplied model
или coordinate shift отсутствует. Нумерация сканов с нуля. Входы синтетические,
это не пройденные метры и не динамический тормозной эксперимент.

| Distractor center | Target lateral / distance, м | Реальная выбранная пара | Результат |
|---|---|---|---|
| +0.4 | +1.29 / 67 | distractor, все 14 track fits | false core 14/14; false target STOP сканы 4–13 |
| +0.6 | +1.50 / 67 | distractor, все 14 track fits | false core 14/14; false target STOP 4–13 |
| −0.6 | −1.50 / 67 | distractor, все 14 track fits | false core 14/14; false target STOP 4–13 |
| +0.6 | +1.50 / 37 | distractor, все 14 track fits | false core 14/14; false target STOP 4–13 |
| +0.4 | −0.68 / 67 | distractor, все 14 track fits | miss 14/14; warning/column, core false |
| +0.6 | −0.68 / 67 и 17 | distractor, все 14 track fits каждого case | miss 14/14 в каждом; core false |
| −0.6 | +0.68 / 67 | distractor, все 14 track fits | miss 14/14; core false |

Для lateral 1.50 весь объект лежит за envelope: ближайший геометрический край
**1.27 м**, зазор **0.22 м**; это не спор на границе. В 67 m case видимые raw
target Y **1.325184..1.674968 м**, ноль raw returns в host body. Эти же target
returns без distractor не дают core/STOP. В wrong case final fitted center при
X=0 **0.613822 м**, ось при target X≈67 м **0.625178 м**. Фактические
`estimate_rails.center/xm/mids` сохранены **на каждом** track/core-anchor вызове
и независимо восстановлены из исходного облака.

Для miss при +0.4/−0.68 объект геометрически внутри host body, raw Y
**−0.889219..−0.539572 м**. Final fitted center ≈**0.388037 м**. Наблюдается
warning/column и column history; при ±0.6 отдельные объекты уже не получают
target candidate в смещённом corridor. Причины не объявлены одинаковыми:
в JSON сохранены реальные returns `_collision_core`/`_advisory_reason` и tracker.

**Механизм false core:** выбранная отвлекающая пара задаёт модель и снова
находится при raw anchor remeasurement. Малые residuals относительно этой
неверной модели и параллельные неизменные стены дают consistency interval,
который не включает семантическую ошибку host center. Eroded body test проходит
в неправильной системе; tracker подтверждает gauge target с пятого скана.
Anchor — наблюдаемая проверка согласованности, не гарантированная truth bound.

**Отрицательный forcing outcome:** `wrong_0.6_1.5_17.0` выбрал **host**, не
distractor, на всех 14 сканах и не дал false core/STOP. Его название сохраняет
намерение пробы, а фактический результат явно помечен в independent reports.
Стандартный host-rise 0.35 м в исследованных screens wrong fit не дал;
этот более узкий wrong-selection сценарий остаётся **UNVERIFIED**.

## Actual no-rail geometry и потеря рельсов

Рельсы удалены из геометрии, не отфильтрованы по меткам после ray-cast.
Все 14 outputs каждого cold start сохранены. Проверены **все candidates**, а
не только совпавший target: новый collision core отсутствует.

* Fresh rail-free scenes: distance 17/67 м, bed −2.18 м; отдельно 67 м с
  исходным rail-free floor −1.83 м. Во всех трёх **0/14 fresh core и 0/14
  target STOP**. В 67 m scene target виден; candidate warning `beyond_axis`,
  `rail_slabs=0`, anchor отсутствует. Отсутствие STOP не означает отсутствие
  физического препятствия — это зафиксированный no-rail limit.
* `loss_target_remains`: сканы 0–13 с actual rails, core подтверждён;
  сканы 14–27 без rails, target остаётся видимым. Core сразу false,
  `collision_core_hits=0`, ready=False. Target STOP **14–17**, warning с **18**.
  Это **zone-vote retention**, не новое core и не missed-frame hold:
  hits продолжаются, misses=0, `zone_hist` постепенно теряет прежние True;
  6/10 ещё достаточно, 5/10 уже недостаточно для unchanged 60% vote.
* `loss_target_absent`: после того же подтверждённого core удалены и рельсы,
  и target. Target STOP только на **14**, `misses=1`; на **15** reported=False,
  `misses=2`. Это bounded tracker missed-frame retention. Сохранявшийся
  `Track.last.collision_core=True` не считается новым измерением.
* `actual_floor_held`: после warmup blocker X=7..9 м, Y=±2 м, top Z=0.8 м
  физически закрывает дальний target и bed, оставляя лучи на roof. На **14–27**
  реальный `_floor_shadow` возвращает hold и `floor_held=True`. Reported
  `rail_slabs=3` удержан от prior при **нуле actual rail returns**. Нового core
  нет; target STOP только 14, затем missed hold исчерпан.
  Сам физический blocker становится отдельным **global STOP с 18** через
  другие правила, без collision core. Global obstacle и target-matched STOP
  сохранены раздельно; отсутствие нового core не трактуется как запрет всех STOP.
* `actual_floor_recovery`: blocker снят и rails возвращены на 21. Core снова
  измеряется с **21**, новый track подтверждает target STOP с **25**.

Первоначальный blocker до самого roof **не** дал `floor_held`: floor fit
вернул prior без этого флага. `loss_shadow_held` — историческое имя неудачной
пробы, не её итоговая категория. Сохранены её outputs и 12-trial floor screen;
реальный held case расположен в **`actual_floor_held.json`**.

Полный pipeline held scene закрывает target; исполнение anchor guard при
одновременно видимом body здесь **не проверено**. Отдельный component с
supplied `floor_held=True` даёт anchor/interval None, строго component-only.

## Положительные контроли и независимая проверка

* Correct-pair lower-host controls: ±0.68 на 67 м — core 14/14, target STOP
  4–13; outside 1.29/±1.50 — core/STOP отсутствуют. Inside 37 м также positive.
  Inside 17 м detector даёт STOP 4–13, хотя near pair не квалифицируется
  (0 slabs) и core отсутствует: это positive detection через другие правила.
  Дополнительный `paired_host_near_center` на **17 м, lateral=0** даёт реально
  выбранный **host** во всех 14 fits, core 14/14 и STOP 4–13: положительный
  правильный-pair/core control на той же ближней дистанции действительно есть.
* Inside distractor controls +0.68 на 17/67 м реально выбирают distractor и
  дают core/STOP; matcher/estimator не «находят ноль» на всех сценах.
* **31 directed full-pipeline sequences / 518 scans**: plain/traced равны по
  каждому non-timing `FrameResult` field (включая raw array dtype/shape/bytes,
  health/mount) и полному tracker state. Свежий независимый replay **из сохранённых
  NPZ**, без tracer и без повторного caster, снова совпал **518/518**.
* В обоих arms previous latency одинаково 42 ms, первая None: устранена только
  обратная связь wall-clock в health. `timing_ms` исключён; latency здесь не измерялась.
* **837** production track/core-anchor estimator calls восстановлены отдельными
  order statistics и weighted covariance fit из raw points; калибровочные
  trial hypotheses сохранены, но не используются как выбранная host-пара и
  отдельно не re-derived.
* **375** target core calls: captured d/h сверены с raw XYZ/model; каждый core
  return независимо проверен scalar rectangle erosion и voxel/height/bottom bars.
  Returns: **252 true, 11 body-bars false, 14 current-support false,
  98 no interval**. Это вызовы, а не число уникальных объектов.
* **361 anchors, 361 intervals**, включая **249** sets четырёх raw boundary
  profiles, независимо пересчитаны. **435** target tracker rows проверены;
  no-rail vote retention пересчитан на всех его строках.
* **1359** raw ray/surface samples проверены отдельным scalar nearest-intersection
  методом; max discrepancy **4.87e−6 м**. Это stated sample, не все лучи.
  Геометрический host-envelope/target-point audit выполнен для всех input rows.
* Exact checker обнаружил один float64 ULP, signed zero, dtype change и
  удаление известного positive detection. Known positives у core/anchor/fit/matcher
  реально выполнены. Исходный test module: **104 passed**.
* Просмотрены raw rows и [raw-examples.png](raw-examples.png), 4 панели случаев:
  видимые host/distractor ridges, outside false STOP, inside miss, no rails.
  Полный target cast сохраняется в NPZ, plotted subset явно не выдаётся за все лучи.

Первый independent verifier остановился на calibration `observe_mount`:
он ошибочно ожидал full-cloud hash для внутренней near/strided hypothesis.
Исправлен scope проверки: все реальные **track/core-anchor** calls проверены;
калибровочные trial fits явно excluded/unverified. Failed log сохранён.

## Component-only и непроверенные границы

`components.json`: supplied coordinate axis 0/±1.59 м со стандартной fixture и
extra outer rail; XYZ/ring/labels сверены с fixture. Для ±1.59 **нет qualified
estimate_rails pair**; core/STOP false. Это не actual wrong-pair proof и не
unmodified pipeline. **Wrong selection на ±1.59 м — UNVERIFIED.**

Не проверены prevalence на реальных записях, curves/motion/другие фазы лучей,
длительное поведение за пределами 14 no-rail scans, G3. Результаты не закрывают
общий H1 и не заменяют отдельный current-miss audit основного агента.

## Артефакты и воспроизведение

* `ACCEPTANCE.json` — итог, каждый case/stage, global/target STOP, all-candidate core.
* `<case>.json` — все full outputs, exact fingerprints, actual estimator returns,
  executed core/anchor/advisory/confirmation returns, candidate и tracker snapshots.
* `raw_*.npz` — compact XYZ/ring/oracle labels; `source.tar.gz` — 45 source/doc/test
  files, каждый member reopened/hash-checked. Tool scripts лежат рядом отдельно.
* `independent-check-complete.json`, `raw-anchor-coordinate-check-complete.json`,
  `fresh-raw-recheck-complete.json`, `selected-raw-snapshots.json` — итоговые
  независимые проверки; предыдущие checkpoints 28/30 sequences тоже сохранены.
* `manifest-before/after/final.json`, `container-member-checks.json`,
  `artifact-manifest.json`, `log-*.log` — source/index/runtime/input/artifact receipts.
  Каждый файл <20 MB; manifest исключает только собственный hash.

Среда для всех скриптов:

```bash
export RESENSE_REPO=/home/aiops/resense PYTHONPATH=/home/aiops/resense
export OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export LD_LIBRARY_PATH=/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu
PY=/tmp/opencode/resense-b4-venv/bin/python
E=$RESENSE_REPO/docs/evidence/h1_rail_limits_2026-10-20
$PY "$E/h1_verify.py" independent-check-rerun.json
```

Для нового полного capture скопировать tools/protocol в **новую разрешённую**
evidence directory и выполнить `h1_run.py`, `h1_controls.py`, `h1_floor.py`, `h1_near_control.py`,
`h1_verify.py independent-check-complete.json`,
`h1_anchor_check.py raw-anchor-coordinate-check-complete.json`,
`h1_recheck.py fresh-raw-recheck-complete.json`, `h1_plot.py`, затем
`h1_package.py`. Для exact historical exploratory screens перед capture также
запустить `h1_explore.py`, `h1_force2.py`, `h1_probe3.py`.
Scripts отказываются перезаписывать evidence JSON. Plotting
при новом окружении запускать с `MPLCONFIGDIR` внутри разрешённого temp parent.
