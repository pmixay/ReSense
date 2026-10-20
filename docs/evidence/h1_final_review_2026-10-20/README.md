# Fresh independent final H1 review — BLOCKED

**Аудит завершён. Приёмка функциональности H1 — BLOCKED; H1 остаётся OPEN.**
Оснований заявить «complete H1», «eliminate 63», проверенную истинную ось на
100–150 м или итоговую safety acceptance нет. На текущих байтах детектора
подтверждены и оставшиеся misses, и conditional wrong-selected-pair failures.

Ревью выполнено новым reviewer, не автором трёх проверяемых audit tools.
Изучены `CLAUDE.md`, `docs/DETECTOR_FREEZE.md`, README/отчёты/scripts исходных
трёх evidence packages, miss-publication allowlist/verifier, rail protocol и
acceptance amendment. Первичный вывод получен своим `review_h1.py`; модули
авторских audit tools им не импортируются. Авторский standalone verifier
запущен отдельно как дополнительная сверка.

## Результат по требованиям

| Требование | Независимо установленный результат | Приёмка H1 |
|---|---|---|
| Устранить 63 remaining visible misses | 114 hit / 63 miss / 177 visible rows; совпали конкретные k, а не только итоговое число | **Не выполнено** |
| Независимый far reference A/C 100–150 м | Все 36 сохранённых direct comparisons не проходят diagnostic gates; withheld validation пересчитана из raw support | **BLOCKED**, валидированная физическая ось не получена |
| Actual wrong-selected pair | Реальный estimator выбирает distractor; есть outside false core/STOP и inside misses при известных host bounds | Проверка завершена, **failures подтверждены** |
| Actual no rails / rail loss / floor held | Все directed outputs проверены; fresh core и retained STOP различены, actual floor-held trace подтверждён | Ограниченные сценарии проверены; общей гарантии нет |
| Final acceptance / reseal / push main | Печать целостности проходит; safety acceptance не следует из неё | **H1 не принимать / не закрывать** |

Это acceptance review evidence, а не исправление детектора или утверждение
частоты ошибок на реальных путях. В пределах этой задачи reseal/commit/push/G3
не выполнялись.

## Реальное исполнение и сохранённые файлы

Успешный итоговый запуск: **2026-10-20 17:25:37 UTC**, **82.99 s**, exit 0,
HEAD **`f56ad5e62d9d051811c804734c7731b6951eae90`**.
Exit 0 означает завершённое ревью, **не успешную приёмку H1**.

* [`review_h1.py`](review_h1.py) — основной воспроизводимый reviewer script.
  Исходные detector/evidence/captures читает; пишет только новый отчёт здесь
  и deliberate freeze-control copy внутри разрешённого temp scope.
* [`report.json`](report.json) — результат реального запуска: все 340 full
  snapshot comparison rows, все 177 matching rows, все 63 miss records с
  компактными executed proofs, все 518 directed rows, rederived fits,
  geometry bounds, hashes, controls и явно ограниченный verdict.
* [`crosscheck.py`](crosscheck.py), [`crosscheck.json`](crosscheck.json) —
  отдельная повторная сверка matching/output rows, текущих source/index hashes
  и script/report identity. Основной reviewer module не импортируется.
* `SHA256SUMS` — текущие checksums файлов этого review package, кроме самого списка.

| Артефакт | SHA-256 |
|---|---|
| `review_h1.py` | `3921a10aa9f52f2e6f6e0972f6ceacda5dd9c154fea05e4811057a33ed955167` |
| `report.json` | `bdd7e94747aff3422d217a824f9327be09f5c1e6c0cdfb9f1da9ca81f533c71e` |

`report.json` — **1,129,271 bytes**. Каждый файл пакета значительно меньше
20 MB. Сами данные воспроизведения остаются в исходных evidence/VM captures;
этот маленький пакет не выдаётся за автономную копию всех point clouds.

## 1. Source, seal и целостность публикации

* Все **52** tracked production/ROS/build files в reviewer inventory совпали
  с HEAD. Все **40** sealed files совпали с текущей R3-печатью, digest
  `6d091081769104657ecc2c0b06f53049647d4f6c7327b7429bbda92673782452`.
* `python3 -B scripts/detector_freeze.py verify` действительно дал PASS.
  Stdlib verifier отдельно запущен на чистой временной копии: PASS. Добавленный
  byte/comment в **копии** `resense/track.py` дал FAIL с именем изменённого файла.
  Репозиторий при positive control не модифицировался.
* Reference source map покрывает **40/40**, rail map — **40/40** sealed files.
  У miss source map покрытие **38/40**: `setup.py` и `pyproject.toml` не включены
  в его source map. Это реальный предел исходного provenance receipt; эти два
  файла в данном ревью отдельно сверены с HEAD и seal. Все 38 пересекающихся
  hashes совпали. Сохранённый hash текущего `resense/_resense_native.so` тоже
  совпал с miss receipt. Несовпадений detector source bytes не обнаружено.
* Source bytes, HEAD и Git index hash до/после **успешного review run** равны;
  это повторно проверено отдельным crosscheck. Index hash review window:
  `5c04ad6dd30a1d089909bd2166ed509e54681e448855a5cdacccf62887b62ec6`.
  Исторические авторские receipts содержат другой index hash (`2c3de1…`);
  историческая byte identity index с текущим состоянием не заявляется.
  Отдельный `git --no-optional-locks diff --cached --name-status HEAD` пуст;
  production working-tree diff также пуст. Reviewer scripts используют
  `--no-optional-locks`; staging/branch commands отсутствуют.
* Пересчитаны sizes/SHA-256 **30** allowlisted miss-publication files:
  **7,460,049 bytes**, largest **5,411,599 bytes**. Checksum set точно равен
  allowlist минус сам список. VM-only archives не входят в allowlist.
* Проверены hashes **126** rail artifact-manifest entries. Для raw NPZ
  дополнительно сверены dtype/shape/XYZ/ring/labels bytes.
* Оба successful miss capture streams полностью SHA-256 checked. Самостоятельно
  пересчитаны все **340** full-snapshot IEEE hashes, frame-result hashes и
  whole processed cloud byte hashes. Lossless projection сверена с original
  captures для всех **177** target supports/outputs и всех **63** miss event /
  tracker / candidate / thin / low-height sets — **3285** branch events.
* Авторский `verify_publication.py --vm` дополнительно прошёл: 340 full snapshot
  hashes, 177 projections, 63 miss projections, **33/33** original production
  checksum entries через storage-map resolver. Это corroboration, не замена
  независимым row comparisons выше.

Полная regression/X3/Falcon battery заново не запускалась: detector source
не менялся. Freeze здесь — проверка целостности, не новый gate и не reseal.

## 2. Все 63 misses: traces, а не labels из финального reason

Успешные raw plain/traced streams независимо сравнены **340/340** по всем
**19** non-timing `FrameResult` fields и полному tracker state, включая массивы
по dtype/shape/bytes и floats по IEEE bits. Сверены exact injection inputs.
Все **177** placements пересчитаны из сохранённых ICP/baseline inputs; matching
заново вычислен из raw detection positions. Второй script независимо получил
те же IDs на каждой из 177 строк.

Для target attribution используются actual injected-return indices и tracker
lineage. Из actual returns/checkpoints заново получены все labels, включая
сопутствующие. Проверены gate predicates, assignment `t.reported`, конечная
zone/payload и early-return parent/child связи, не только наличие имени ветки.

| Primary executed mechanism | Строк |
|---|---:|
| Column hold | 43 |
| Beyond axis limit | 9 |
| Zone vote delay | 7 |
| Merged wall-segment filter | 2 |
| Height-reference limit | 1 |
| Tracker unconfirmed | 1 |
| **Всего** | **63** |

Все labels, с пересечениями: column hold **43**, actual column demotion **20**,
axis **9**, vote delay **12**, tracker unconfirmed **7**, wall merge **2**,
height reference **1**. Primary — приоритет в описании наблюдаемого пути,
не экспериментально доказанная единственная counterfactual root cause.

На miss rows достигнут **61** core predicate: no interval **41**, insufficient
current support **1**, footprint **1**, failed body bars **13**, accepted core
**5**. На двух wall-merge rows происходит более ранний return. Для дошедших
body masks использованы независимые прямые rectangular inequalities вместо
production polygon XOR и авторского crossing-number checker. Пересчитаны
current/retained indices, distinct voxels, vertical span и bottom bars.

На k319–323 уже есть accepted core, но hold ещё действует; k323 core span
**0.49992799758911133 s**, а порог **0.5 - 1e-9 s**. k324 — совпадающий hit.
Это не «63 исправлены»: свежие captured outputs содержат прежние 63 miss k.

Просмотрены напечатанные raw XYZ/extents **10** кадров:
k152/159/174/177/178/196/224/306/319/323; примеры сохранены в report. В частности,
k177/k196 длинным становится слитый с фоном cluster, а не сама injected body:
её observed X extent **0.0245 / 0.0341 м**. Дальняя sparse sampling не выдаётся
за измеренную полную форму объекта или реальную дальность торможения.

Positive controls: k164 содержит реальный matching hit; удаление detection,
один float32 ULP, signed zero и dtype change обнаружены exact comparator;
удаление actual column-held branch k224 лишает атрибуцию подтверждения;
изменённый core-mask bit k319 отклонён независимой эрозией. Planted added k164
и removed k152 обнаружены set comparator. Все назначенные категории имеют
реальные executed positive examples; actual accepted core, released hold и
qualified tracker также присутствуют.

Injection axis по-прежнему является **cached detector baseline**, не независимо
измеренной осью. Совпадение placement calculation не создаёт external truth.

## 3. Wrong pair: rederived raw fit и независимые host bounds

Независимо replayed **31 full-default-detector sequences / 518 scans** из
сохранённых NPZ, без повторного caster и без tracer. **Каждый** non-timing
output field и полный tracker state совпали с original exact captures.
Также на каждой строке заново сверены matching detections/warnings/candidates,
global STOP, any-candidate core, selected pair и стадии исходного acceptance.

Из processed raw points самостоятельно восстановлены все **837** actual
track/core-anchor `estimate_rails` calls (**669** distinct recomputations):
near selection, height order statistics, ridges, slab peaks, weights, absolute
midpoints и center/tangent fit. Для regression использованы weighted 2×2 normal
equations. Calibration `observe_mount` trial fits в это число не входят.
Planted +0.10 м в captured fit center отклонён raw reconstruction.

Геометрическая истина fixture: host center=0, heads Y=±0.795 м; envelope
|Y|≤1.05 м, h=0.12..3.0 м над **host** head. В lower-host cases head Z=**−1.98 м**
(bed −2.18 + rise 0.20), target base остаётся −1.83 м. Raw bounds/body membership
пересчитаны на всех directed inputs. **1359** raw ray/surface samples независимо
проверены scalar nearest-intersection методом; max error **4.8645e−6 м**.
Это stated sample лучей, не полная повторная генерация каждого ray.

Конкретные подтверждённые контрпримеры:

* `wrong_0.6_1.5_67.0`: actual distractor fit **14/14**, false target core
  **14/14**, target STOP **4–13**. Геометрический ближайший край Y=**1.27 м**,
  зазор за host envelope **0.22 м**; raw target Y=**1.325184..1.674968 м**,
  raw body points **0**. Final model center **0.613822115 м**. При тех же outside
  target returns без distractor false core/STOP отсутствует.
* Outside false core/STOP также подтверждены для +0.4/+1.29/67,
  −0.6/−1.50/67 и +0.6/+1.50/37. Это четыре sequences, по 14 core /10 STOP rows.
* `wrong_0.4_-0.68_67.0`: target intersects host body; raw Y=
  **−0.889219..−0.539572 м**, final center **0.388036859 м**, target STOP **0/14**.
  Ещё три inside miss sequences полностью перепроверены. Причины не объявлены
  одинаковыми по одному только отсутствию STOP.
* `wrong_0.6_1.5_17.0` фактически выбирает **host 14/14** и не даёт false core;
  сохранённое имя пробы не принимается за её результат.

Есть реальные положительные correct host/core/STOP controls на **17 и67 м**,
outside correct-pair controls и inside distractor/core/STOP controls. Неверная
семантика host не ограничивается малым consistency residual: anchor может
повторно найти ту же distractor pair. Наблюдаемая согласованность не является
гарантированным bound истинного пути поезда.

Это физические synthetic rail-like AABB ridges высотой 0.20/0.30 м, а не точный
профиль рельсов или внешняя аннотация реальной записи. Wrong selection при
standard host-rise 0.35 м, actual offset ±1.59 м, prevalence, curves/motion
и универсальное покрытие остаются **UNVERIFIED**.

## 4. No rails: current core, retained STOP и floor-held

Все перечисленные сканы независимо replayed и сверены по полному state:

* Три cold-start rail-free scenes: **42 scans**, actual rail returns=0;
  fresh any-candidate core **0/42**, target STOP **0/42**. Положительные controls
  находят rails/core/STOP. Эта bounded absence не означает отсутствия препятствия.
* `loss_target_remains`: после удаления rails новый core сразу false; target
  всё ещё виден, hits продолжаются, misses=0, core_hits=0, core_ready=False.
  STOP на **14–17** воспроизводится **zone vote retention**: **6/10** ещё проходит,
  **5/10** уже нет. Это не новая core evidence и не missed-frame hold.
* `loss_target_absent`: target STOP только **14**, misses=1; **15** уже unreported,
  misses=2. Старое `Track.last.collision_core` не считается новым измерением.
* `actual_floor_held`: **14–27** actual `_floor_shadow` returns hold=True,
  model floor_held=True. Сохраняются prior `rail_slabs=3`, хотя actual current
  rail returns=**0** и target returns=**0**. Target STOP только **14**;
  отдельный физический blocker даёт **global STOP с18** по другим правилам.
* Recovery: rails/target возвращены на **21**, target core возобновлён;
  matching target STOP с **25**. Case с историческим именем `loss_shadow_held`
  не даёт floor_held — это также явно проверено.

В actual held scene blocker закрывает target. Full-pipeline guard с одновременно
видимой target body не доказан; supplied held-model component test не закрывает
эту границу. Поведение дольше 14 no-rail scans не проверялось.

## 5. Far reference и raw topic spot check

Из portable trajectory archive независимо rederived **36/36** direct-comparison
decisions по сохранённым matrices, rotation через **acos(trace)**. Результат:
**0 PASS**; first failures **4 seed /24 reverse translation /7 reverse rotation /
1 fitness**. Известный manufactured 80 м rigid control проходит; четыре planted
faults отклоняются соответствующими gates. Повторного ICP не было.

Пересчитаны все **5903** observation centroids непосредственно из raw support
через `math.fsum`; все **55 withheld tracks /1185 observations** через poses и
scalar distances. p95≤0.10 м: **A13/28, C16/27**; все p95 совпали с saved records
до1e−12 м. Эти residuals смешивают sampled centroid, association и pose errors,
а не дают чистую независимо измеренную pose-error distribution.

Original SQLite A/C отдельно открыты read-only. Другим SQL grouping пересчитаны
topics/message counts: **A545, C268**, только PointCloud2. Ненулевые cloud counts
дают same-query positive controls. Прежняя 11-bag inventory и live-source checks
переиспользованы; полные ~64 GB заново не хешировались. Указанные пользователем
DK6…/Falcon и `SfBeRHbs8bNJAQ/folder6` — provenance данных, **не external rail /
pose truth**. Общего утверждения об отсутствии любой возможной внешней информации нет.

Для снятия far-reference blocker нужны независимо проверенные left/right rail
heads и path identity в конкретных A/C frames100–150 м с quantified uncertainty;
либо независимо валидированные synchronized relative SE(3), extrinsics/error
budget и проверенные near-rail observations. Новый ICP-chain сам по себе этого
не заменяет.

## Воспроизведение на VM

Из корня checkout, с уже существующим data/runtime layout:

```bash
export RESENSE_REPO="$PWD" PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export LD_LIBRARY_PATH=/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu
/tmp/opencode/resense-b4-venv/bin/python -B \
  docs/evidence/h1_final_review_2026-10-20/review_h1.py \
  --out docs/evidence/h1_final_review_2026-10-20/report-repeat.json
```

Output filename должен быть новым: overwrite запрещён. Требуется NumPy и
существующий detector runtime. Скрипт делает только bounded directed replay;
записи A читает из сохранённых captures. Temporary freeze controls остаются в
`/tmp/opencode/h1-final-review/freeze-control-*`. `crosscheck.py` читает исходный
`report.json` и эксклюзивно создаёт `crosscheck.json`; повторный запуск требует
нового output имени в копии этого вспомогательного script.

## Исправления собственного reviewer verifier

До успешного отчёта были остановившиеся проверки, сохранённые только в
`/tmp/opencode/h1-final-review/`:

1. Raw gauge profile содержит tuples; первоначальное list equality заменено
   numeric equality без изменения геометрии/порогов.
2. Удаление единственной primary branch k224 закономерно вызывает unresolved
   attribution; это учтено как ожидаемый rejected positive control.
3. Фактический caller estimator — `estimate_track`; исправлен первоначальный
   неверный фильтр `track` при stage accounting.
4. Алгебраически эквивалентная NumPy percentile interpolation меняла IEEE ULP
   ties и могла выбирать соседний ridge bin. Independent implementation теперь
   использует documented weighted order-statistic arithmetic, затем свой
   normal-equation solve. Требуемая точность проверки не ослаблялась.

После исправлений выполнен полный успешный review run; затем отдельный
`crosscheck.py` заново сверил **177 raw matching rows +518 directed output rows**
и все52 source files. Исходный detector и старое evidence не редактировались.

**Итоговая рекомендация: аудит принять как завершённый; H1 feature acceptance
оставить BLOCKED/OPEN. 63 misses не устранены, независимый true axis не создан,
wrong-pair failures подтверждены; универсальной safety guarantee нет.**
