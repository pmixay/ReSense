# Независимый P4: H1 / свежий A-axis replay и remaining visible misses

**Итог: 340 кадров, 177 visible rows, 114 hit, 63 miss. Все 63 miss атрибутированы
по исполненным веткам и полным snapshots.** Историческое множество miss-строк E
совпало точно: добавлено 0, удалено 0. Это полученный результат, а не заданная цель.

Evaluation checkout: `main`,
`f56ad5e62d9d051811c804734c7731b6951eae90`. Протокол [PROTOCOL.md](PROTOCOL.md)
сохранён до replay. Прочитаны `CLAUDE.md` и `docs/DETECTOR_FREEZE.md`;
актуальная R3-печать прошла `verify` до и после работы: 40 файлов, digest
`6d091081769104657ecc2c0b06f53049647d4f6c7327b7429bbda92673782452`.

**Injection axis — cached detector baseline, не внешняя истина.** Результаты
не устанавливают independently in-gauge placement, реальную дальность или
достаточность торможения. Wrong-selected-rail-pair/no-rails рассмотрены main agent
в отдельном [h1_rail_limits evidence](../h1_rail_limits_2026-10-20/README.md).
Общий H1 этим аудитом не закрывается.

**Publication edition.** Intended public subset и команды offline-проверки —
[PUBLICATION.md](PUBLICATION.md), точный allowlist — `publication-manifest.json`.
Публикационный subset подготовлен из существующих captures без повторного replay.

## Acceptance и фактически выполненные проверки

| Проверка | Фактическое покрытие / результат |
|---|---|
| Plain/traced, без округления | 340/340: все 19 non-timing полей `FrameResult`, включая `xyz`, candidate/track arrays, health и mount |
| Exact raw fingerprints | 340/340; дополнительный независимый IEEE-754/array-byte comparator и SHA-256 в `ieee-exact-check.json` |
| Input equality | 340/340 fingerprints injected XYZ/intensity/ring/metadata; полные file SHA-256 cache, ICP и baseline до/после равны |
| Full-precision hit matching | 177/177 visible rows: raw detection positions против исходных `X/Y`, затем отдельный interval-containment метод |
| Округление judged evaluator | Его сантиметровые `X/Y` проверены отдельно; hit-множество совпало с full precision на 177/177 |
| Независимое восстановление placement | 177/177: ICP median-of-7/clipping/cumulative travel и polynomial baseline Y, ошибка <1e-12 м |
| Attribution | 63/63: реальные return/checkpoint events, target-return provenance, состояния кандидатов и трекера, финальные detection/warning payloads |
| Core mask | Все 172 target core calls на 177 visible rows; scalar horizontal polygon intersections против captured mask, voxel/height/bottom bars |
| Source/index | Source/input bytes, HEAD/main и SHA-256 Git index равны начальным; freeze PASS |
| Raw examples | Просмотрены 10 кадров: k152/159/174/177/178/196/224/306/319/323, raw rows и `raw-examples.png` |
| Архивы | Каждый member повторно открыт, размер и SHA-256 сверены с исходным файлом |

Сравнение исключает **только `FrameResult.timing_ms`**. Health latency не вырезана:
перед каждым физическим вызовом имеющийся `_previous_latency_ms` заменён на
одинаковые **42 ms**; после reset/первого кадра `None` сохраняется. Это устраняет
обратную связь wall-clock instrumentation в health. Этот запуск не измеряет latency.

Positive controls действительно выполнены на известном hit k164:
потерянный hit label и удалённый detection payload обнаружены независимым matcher;
изменение raw detection distance и одного float32 ULP в `xyz` обнаружено comparator
и fingerprints; timing-only изменение игнорируется. Отдельно IEEE comparator
обнаружил float ULP, signed zero, dtype и shape. Компаратор исторических множеств
обнаружил planted added k164 и removed k152. У всех назначенных классов есть
реальные положительные executed examples; принятие core, qualified tracker,
gauge vote и снятие column hold также наблюдались на неизменённом replay.

## Все contiguous miss intervals

`k` — нулевая нумерация evaluator. Диапазоны X ниже округлены только для таблицы;
в JSON координаты полные. Primary — наблюдаемый механизм miss, остальные
одновременно действовавшие gates сохранены в `all_misses[].checks/labels`.

| k inclusive | Miss count | X, м, начало → конец | Primary mechanisms |
|---|---:|---:|---|
| 152–163 | 12 | 228.356 → 219.234 | axis limit 7; zone vote delay 5 |
| 171 | 1 | 212.374 | axis limit |
| 174 | 1 | 209.628 | tracker confirmation |
| 176–180 | 5 | 207.766 → 203.988 | axis 1; merged wall segment 1; height reference 1; zone vote 2 |
| 196 | 1 | 188.065 | merged wall segment filter; missed-frame hold exhausted |
| 224–239 | 16 | 157.046 → 138.845 | column hold |
| 248–256 | 9 | 127.330 → 116.786 | column hold |
| 306–323 | 18 | 44.855 → 19.752 | column hold |
| **Всего** | **63** | | **43 column hold + 9 axis + 7 vote + 2 structure + 1 height + 1 confirmation** |

### Реальные checked rules

* **43 column hold:** `Track.column_held` (`tracking.py:129–130`) вернул True;
  сумма column history >= threshold, `collision_core_ready=False`;
  `rule_zone` исполненно возвращает warning. В **20 из этих 43** кадров
  `_advisory_reason` дополнительно реально вернул `column` (`clustering.py:756`):
  narrow/tall shape, отсутствие принятого core, ветка free-top не освобождает.
  Остальные hold-строки не переименованы в новую column demotion.
* **9 axis limit:** return `beyond_axis`, `clustering.py:734`; проверено фактическое
  `dist > axis_valid`, cluster zone и итоговая ветка tracker/output.
* **7 vote delay:** `Track.vote_zone`, `tracking.py:136`, реально вернул warning,
  затем `rule_zone:153` использовал именно его. Проверены numerator,
  `max(history_length, zone_min_votes)` и threshold. Чистый текущий gauge hit
  не стирает историю прежних advisory hits.
* **2 merged wall segment:** k177 и k196, `_is_infrastructure:376` → True,
  `_corridor_cluster:1121` → None. Кластеры включают injected indices и фон:
  observed sizes около `[5.103,1.056,2.220]` и `[5.300,1.162,2.883]` м;
  executed rule требует height > wall_min_height, length >4 м, width <1.5 м.
  Raw injected body сам имеет X extent лишь 0.024/0.034 м: это слияние с фоном,
  а не физический объект длиной 5 м. На k177 удержан warning; на k196 второй
  miss исчерпывает `hold_misses=1` и reported становится False.
* **1 height-reference limit:** k178, `clustering.py:737`; дистанция за поддержкой
  height reference и длина merged cluster 5.080 м > `far_max_length`.
* **1 primary confirmation:** k174, `_qualifies:983` → False;
  2 hits <3 и span 0.400019884 s <0.5 s. На k152–156 и k171 обычное
  неподтверждение тоже реально действует, но там primary — axis limit.

Для каждого miss сохранены executed `_corridor_cluster` / `_advisory_reason`,
core return (если predicate достигнут), `_qualifies`, `t.reported` checkpoint,
zone properties и финальные track/output snapshots. Повторные Python line events
на одной многострочной assignment проверены на идентичность состояния.
Каузальные labels не получены только из `Cluster.reason`.

### Почему collision core не снимает эти misses

На 63 miss-строках predicate достигнут в 61 кадре; на k177/k196 infrastructure
filter возвращает раньше. По фактически исполненным returns:

| Core result / executed exit | Miss rows |
|---|---:|
| Нет consistency interval; проверено insufficient near/local boundary station support (`:470`) | 41 |
| Current support ниже core bar, k157 (`:1036`) | 1 |
| Footprint guard, k178 (`:1032`) | 1 |
| Final robust body mask/bars не проходят, k306–318 (`:1045`) | 13 |
| Core принят, k319–323; tracker hold ещё действует | 5 |

Сохранены сами masks, retained indices, unique-voxel/height/bottom bars, интервалы
и actual return paths; scalar polygon cross-check независим от production mask.
Sparse/thin/min-points admission записана для target corridor calls: основной
miss не приписывался sparse/height/confirmation по внешнему виду точек. Этот
аудит не сертифицирует отключённые или неисполненные guards.

**Важная временная граница:** k319 core впервые True; на k323 уже 5 core hits,
но span **0.49992799758911133 s**, что меньше `0.5 - 1e-9`.
На k324: 6 hits, **0.5999060869216919 s**, ready=True и совпадающий STOP.
Это фактически исполненный порог `Tracker._note:731–734`, а не новая причина,
восстановленная постфактум по числу кадров. Полный k318–325 run —
`ieee-exact-check.json:core_release_run`.

## Историческое сравнение и границы

Ожидаемое E-множество восстановлено из трёх сохранённых judged outputs внутри
`h1_reference_2026-10-19/raw-evidence.tar.gz`, затем независимо из raw detection
positions `trace-ranges-e.json`. Все три archived sets и raw re-derivation равны.
Свежие R3+F1a совпали **по каждому k**, не только по числу 63.
Положительные planted added/removed controls проверяют сам set comparator.

Первый совпадающий STOP по judged summary —218.38 м; pooled held90 —19.75 м.
**Pooled held90 не является непрерывной дальностью.** Дальний sparse ray sampling
и исходная baseline-axis placement не дают независимого физического подтверждения.
Forward injection steps 0.816–1.496 м за кадр; raw object extent/count проверены
на всех 177 visible rows. Проверки правдоподобия не превращают ICP или cached
baseline в validated true trajectory/axis.

## Portable publication subset

Публиковать только allowlist `publication-manifest.json` и
`SHA256SUMS-publication`. Это компактный производный evidence; полный raw capture
в public subset не входит.

* `publication-evidence.json.gz` — все **177** exact input-placement/output/matching
  rows, исходные placement inputs, raw/processed target returns, все **63** miss
  snapshots с **3285** captured branch events, core masks/bars, local candidate
  support и tracker states. Ndarrays сохранены без округления как dtype/shape/bytes.
* Whole-scene raw/processed clouds опущены. Для каждого из **340** full snapshots
  записаны canonical IEEE SHA-256 и hashes исходного capture; hashes whole processed
  clouds записаны отдельно. Это ссылки на VM evidence, а не опубликованные clouds.

* [report.json](report.json) — итоговый strict JSON: все 63 miss rows, labels,
  executed rule references/states, 177 full-precision matching rows, exact hashes.
* [ieee-exact-check.json](ieee-exact-check.json) — дополнительная exact byte/IEEE
  проверка всех 340 результатов, controls и core release run.
* [core-rule-checks.json](core-rule-checks.json) — все 172 target core calls и bars.
* `raw-examples.png` — 10 просмотренных raw examples.
* `manifest-before.json`, `manifest-after-replay.json`, `manifest-final.json`,
  `runtime-libraries.json` — hashes и исторические runtime/source/input receipts.
* `storage-map.json`, `historical-receipt-verification.json` — old/new paths,
  hashes и проверка сохранности исторических production bytes.
* `publication-checks.json` — offline и VM projection checks, positive controls.

### VM-only storage: не включать в публикацию

В `/tmp/opencode/h1-miss-audit/vm-only/` **перемещены, не удалены**:

| Файл | Bytes |
|---|---:|
| `raw-captures.tar.gz` | 1,009,663,897 |
| `miss-snapshots.pkl.gz` | 68,835,044 |
| `report-initial.json` | 31,918,404 |
| `inspection.json` | 13,554,124 |

Там же сохранены исходные `README.production.md` и `PROTOCOL.production.md` перед
publication-правками. Hash каждого переноса/backup, old/new path и разрешение
исторического имени — в `storage-map.json`. Полный raw archive SHA-256 остаётся
`5e6519cff0a1c9cce8d8e8cd9088252c5320940ecbe6afd30078cd3815651f7f`.

Исходные `plain.pkl.gz`, `traced.pkl.gz`, failed-attempt capture и логи остаются
в `/tmp/opencode/h1-miss-audit/`. Decoded cache и cached baseline/ICP не изменены.
`source-tools-input-metadata.tar.gz` остаётся на evaluation VM в audit dir и
**исключён из public allowlist**. Все прочие файлы audit dir, не названные allowlist,
также не входят в intended publication.

### Исторические checksum receipts

`SHA256SUMS`, `artifact-manifest.json`, `archive-manifest.json` и
`checksum-verification.json` сохранены **без изменения байтов** как original
production artifact records. Их paths и положительная production-проверка —
исторические. После переноса больших файлов и publication-редакции двух документов
они не являются checksum list текущей portable directory.

Для current portable subset применяется **только `SHA256SUMS-publication`**.
На VM старый список проверяется через resolver `storage-map.json`: все 33
оригинальные записи совпали, включая перемещённые файлы и исходные версии docs.

`audit.py` — replay/capture/первичная проверка; `verify_audit.py` — независимое
восстановление matching и всех labels; `package_audit.py` — IEEE check/упаковка;
`render_examples.py` — исторический график из captures. Public-проекция создаётся
`build_publication.py`, проверяется `verify_publication.py`; publication metadata
фиксируется `finalize_publication.py`. Итоговая атрибуция — в `report.json`.

## Проверка публикационного subset без detector/replay

```bash
# Из directory с intended portable files; только Python stdlib:
sha256sum -c SHA256SUMS-publication
python3 verify_publication.py

# На evaluation VM с имеющимися original captures и NumPy:
PYTHONDONTWRITEBYTECODE=1 /tmp/opencode/resense-b4-venv/bin/python \
  verify_publication.py --vm
```

Историческая judged invocation внутри replay driver фиксирована:

```bash
range_test.py \
 /tmp/opencode/r3-h1/baseline/cache/roundT_squareT_pressureGate_squareT \
 /tmp/opencode/r3-h1/baseline/icp_roundT_squareT_pressureGate_squareT.json \
 /tmp/opencode/h1-miss-audit/range-plain \
 --obj 0.3,0.3,2.8 --start 150 --d0 230 --end 340
```

Обычный range CLI сам по себе не устанавливает deterministic previous latency;
для exact проверки используется wrapper. Существующий `_baseline.json` читается
как зафиксированный input; его отсутствие вызывает отказ до запуска, чтобы не
создать файл рядом с чужим cache.

## Исправленные ошибки аудитора и препятствия

Первый traced attempt остановился на k~250 из-за float local `b` в interval
function: аудитор ошибочно счёл его blob. Исправлен type guard только в evidence
script; полный plain capture переиспользован после source/input equality check;
полный traced replay запущен заново. Failed stream/log и `audit-attempt1.py`
сохранены. Проверка assignment сначала ожидала единственный Python line event;
после обнаружения повторных identical events на multiline expression она проверяет
их равенство. Ни одно failed/partial выполнение не используется как итог.

Первичная геометрическая выборка включала соседние background tracker failures
на k310/k314; итоговый verifier требует actual injected-return provenance и убирает
эти ложные contributing labels. Первичный trace-difference control оказался в
недостигнутой visibility ветке; итоговый control явно выполнен на positive k164.
Финальный status comparator сначала исключал audit-каталог только из конечного
состояния; исправлено симметричное сравнение, поскольку начальный manifest уже
создан после регистрации protocol. Source/input/index сравнения при этом прошли.

Технических препятствий для requested replay/атрибуции не осталось.
Внешняя true-axis/in-gauge reference этим аудитом не установлена. Detector, tests,
существующие evidence, branches и index не редактировались; commit/push/G3 не было.
