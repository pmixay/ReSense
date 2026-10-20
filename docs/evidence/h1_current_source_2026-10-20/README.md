# H1 current-source delta acceptance — 520e7dc

**Delta-аудит завершён. Старые H1 blocking findings воспроизведены на `520e7dc`
точно в проверенных inputs. H1 acceptance остаётся BLOCKED / OPEN.**

Fresh plain replay дал **0 отличий на858 output rows**: 31 directed sequences /
518 scans и A340. Проверены все19 non-timing `FrameResult` fields; для directed
также полный tracker state, для A — все поля сохранённых в старых captures
target-window tracks. Все63 miss k сохранились. False core / STOP в wrong-pair
scenes также сохранились. Независимая true axis этим delta check не создана.

## Закреплённый source и границы работы

* Исполнялся только isolated worktree `/tmp/opencode/h1-reviewed-publication`,
  HEAD **`520e7dcd2843a0e7c9055fca6c186c0d1687945f`**.
* Сравнение — successful captures измеренного
  **`f56ad5e62d9d051811c804734c7731b6951eae90`**. Исходный f56 review report и
  script проверены по прежним hashes и остались неизменными.
* `RESENSE_REPO` и `PYTHONPATH` указывали только на isolated worktree. Пути всех
  загруженных detector/evaluator modules проверены. Concurrent HEAD исходного
  `/home/aiops/resense` не использовался для исполнения; оттуда только читались
  старое evidence и разрешённый existing native binary.
* Единственная detector-source delta — `resense/lowobj.py`. Все52 current
  production/ROS/build files сверены с pinned HEAD, все40 sealed files — с
  текущей F1a-печатью. До/после replay source/HEAD/worktree-index hashes равны;
  отдельный verifier повторил проверку. Worktree index:
  `7aefca959f975a0586bfd6106a9e73ccf91dbeb5cce4879407e44037ce3c41b7`.
* Native sources/build inputs (5 файлов) совпали с f56 и существующим source
  перед копированием `.so`. Скопирован тот же binary, hash ниже; native реально
  загружен из нового worktree. Rebuild не выполнялся.

### Точные ключевые hashes

| Файл/идентификатор | SHA-256 |
|---|---|
| `resense/lowobj.py` на f56 | `6474e3dbff005fa8f6a8ed2c2122608c1f55df33dfe981b14451b595410069e1` |
| `resense/lowobj.py` на520 | `05fee7e78b31acceeff8e47ba789a96a7de086cfefc3451dac750f0220c437a1` |
| `resense/_resense_native.so` | `67fa0887e5480e24ca67138ec5271969742917a5c5869d9ab4e634599d8c7394` |
| Current F1a seal digest | `9cc33a6838dcc30b3162bbf892d33a962008712060e12d68c363dc315d033507` |
| Current manifest file | `9d4bbd499667bef8fc1821885659af111c858b047abefec63d8fc0889510098e` |
| `recheck_current.py` | `1d4291541bfbd5c942740830b2e4c028205b2d252bb8ff1dd6cd9a47c4a79b1c` |
| `current-report.json` | `aa46dcc82e83e097dbb61300df7321f4e4a89fec7e1693b7c84b52e1ce797680` |

Default manifest действительно **`detector_freeze_2026-10-20_1.2.0_f1a.json`**,
не прежний R3. Stdlib `detector_freeze.py verify` дал PASS. На отдельной чистой
копии verifier также дал PASS; deliberate byte/comment change в копии
`resense/lowobj.py` обнаружен с точным именем файла. Source worktree при positive
control не менялся. Это integrity verification, не новый reseal или safety gate.

## Фактическое покрытие и output delta

Успешный запуск завершился **2026-10-20 17:51:51 UTC**, exit0,
**105.40 s** вместе с targeted tests. Первый полный запуск прошёл; failed или
partial captures не использованы.

| Проверка | Измеренный результат |
|---|---|
| Directed NPZ replay | **31 sequences /518 scans** |
| Directed все19 non-timing fields + весь tracker | **518 equal, 0 changed rows** |
| Directed target detection/warning/candidate matching | Пересчитан на всех518 строках; matching changes **0** |
| Fresh A с прежним injection driver | **340 frames**, input fingerprints **340/340 equal** |
| A все19 raw non-timing output fields | **340 equal, 0 changed rows** |
| A original stored target-window trackers | **340 equal, 0 changed rows** |
| A exact visible matching | **177 rows: 114 hit /63 miss**; добавлено0 /удалено0 misses |
| Second-method raw verification | Все340 current A rows против **обоих** old plain/traced captures; все518 directed rows заново сверены |
| Unchanged H1 test module | **104 passed**, 0 failures/errors/skips;11.48 s |

Сравнение не округляет floats: dtype/shape/bytes у arrays, IEEE bits у scalars.
Исключён только `FrameResult.timing_ms`. Existing previous latency нормализована
до **42 ms**, первый вызов сохраняет `None`, как в старом capture protocol.
Health/mount/clear-distance не исключались. Это не latency benchmark.

`row-differences.json.gz` содержит **`{"directed":[],"A":[]}`**. Основной driver
умеет сохранять каждый changed field/leaf/array hash и не останавливается только
из-за output difference. Здесь различий действительно не оказалось, в том числе
в полях, которые мог бы изменить новый low-object path.

## 63 misses и wrong-pair findings

Exact miss intervals A:

```text
152–163; 171; 174; 176–180; 196; 224–239; 248–256; 306–323
```

Сумма — **63**, а не только совпадающий aggregate count. Fresh judged outputs:
114 STOP /58 CAUTION /5 GO /0 FAULT на177 visible rows. Nominal100–150 м:
**20/39 hits**. Baseline/ICP placement по-прежнему detector-relative; эти числа
не означают независимо установленную физическую дальность торможения.

На каждой directed строке заново вычислены matching, raw body membership и
геометрический gap относительно fixture host envelope. Отдельный verifier
пересчитал target core через majority **actual target-return provenance** в
candidate points, независимо от primary distance/centroid matcher.

* Четыре outside wrong-pair sequences: **56 false-core rows /40 false target-STOP
  rows**. В каждой core True на0–13, STOP на4–13. Cases:
  `wrong_0.4_1.29_67.0`, `wrong_0.6_1.5_67.0`,
  `wrong_-0.6_-1.5_67.0`, `wrong_0.6_1.5_37.0`.
* Для lateral±1.50 м ближайший край за envelope на **0.22 м**. Физическая истина
  host здесь задана fixture. Lower-host head Z=**−1.98 м**, а не−1.83 м.
* Inside-miss sequences и paired positive controls сохранены строка-в-строку.
  `wrong_0.6_1.5_17.0` по-прежнему не является actual wrong-selection success:
  старый selected fit — host; current model/outputs совпали с ним.
* Все518 current track-model outputs точно совпали с original captures.
  Rail-estimator source не менялся; независимое raw fit derivation **837 calls**
  остаётся в исходном f56 review. Fresh run здесь plain, без нового tracer:
  old actual branch/fit traces не переименовываются в новые520 traces.

Для позднего column hold отдельный verifier посмотрел raw current snapshots:
k319 core_hits=1; k323 core_hits=5, span=**0.49992799758911133 s**, ready=False;
k324 core_hits=6, span=**0.5999060869216919 s**, ready=True и совпадающий STOP.
Исходные causal labels остаются f56 trace evidence; здесь доказана сохранность
новых outputs и всех сохранённых target-track state fields.

## No rails / retention на текущем source

Все соответствующие outputs/states также идентичны original captures:

* Три rail-free cold starts: **42 scans**, fresh any-candidate core **0/42**,
  target STOP **0/42**. Correct-pair/core/STOP controls остаются положительными.
* `loss_target_remains`: после removal rails target STOP **14–17**, дальше warning;
  current core false, misses=0. Сохраняется прежняя zone-vote retention.
* `loss_target_absent`: target STOP только **14**, затем hold исчерпан.
* `actual_floor_held`: сканы **14–27** floor_held=True, `rail_slabs=3` из prior,
  actual rail returns=0 и target returns=0. Target STOP только14; отдельный blocker
  даёт global STOP с18. Нулевой current core не запрещает STOP по другим правилам.
* Recovery: fresh core с21, matching target STOP с25.

Пределы старого ревью остаются: full-pipeline held case скрывает target; visible
body + held guard, standard0.35 м-host actual wrong selection, actual±1.59 м wrong
selection, curves/motion, persistence дольше14 no-rail scans и real-world prevalence
не принимаются как проверенные. Универсальная гарантия не установлена.

## Inputs, controls и второй независимый способ проверки

Полностью SHA-256 checked **548** fixed cache/baseline/ICP files,
**609,128,672 bytes**, против первоначального input manifest. Полные hashes
по каждому файлу — `current-report.json:inputs.fixed_cache_baseline_icp_files`.
Baseline не пересоздавалась. Все original injection/test/fixture source bytes
сверены с f56; использован evaluator из pinned worktree.

Old captures, полностью hashed и сохранены:

| Capture | SHA-256 |
|---|---|
| Old plain | `69c8cbc566bf4ee7d28dbf7af78a9da246cfadb1d05e6b4fded67235dcad8f61` |
| Old traced | `117987539f3e8e9e2c921fc795f9cf761d74cc1b716935189adfea34d0d82483` |
| Current directed | `feed8b196fafea3da9e80688e31588321a5e0cbe86d4ae9df183480da9095afd` |
| Current A | `412fd3f57ec401562da5774bea3baf6dbb9f247b457bb439260ee2c1ecff8878` |

Primary matcher сверяется с independently expressed absolute-distance matcher.
Positive controls реально исполнены: positive A hit k164, удалённый detection,
float32 ULP в raw XYZ, signed zero, dtype change, planted added/removed miss row;
clean/tampered freeze copy. Для directed есть реальный positive matching/core/STOP.

`verify_current.py` не импортирует detector или primary recheck module: другим
typed normalization сравнивает raw captures, повторно считает matching и через
target-return provenance — false core. Он подтвердил all858 rows,63-set,
retention/held snapshots, current source/index identity и неизменность исходного
f56 report/script. Raw target examples просмотрены в stdout на12 A frames,
включая positive k164/k324 и поздний release; exact snapshots сохранены в captures.

## Артефакты и команды

Portable evidence здесь, каждый файл<20 MB:

* [`current-report.json`](current-report.json) — **1,732,965 bytes**, реальный run;
  current source/input hashes, все858 row receipts, all-field diff accounting,
  independent matching/false-core counts, test/source/runtime receipts.
* [`recheck_current.py`](recheck_current.py), [`PLAN.md`](PLAN.md) — executed driver
  и заранее записанный bounded check plan.
* [`row-differences.json.gz`](row-differences.json.gz) — все обнаруженные различия;
  в этом запуске оба списка пусты.
* [`verify_current.py`](verify_current.py), [`verification.json`](verification.json)
  — отдельная raw-capture проверка.
* `tests104.xml`, `tests104.log` —104 реально исполненных теста.
* `SHA256SUMS` — checksums только этого delta evidence, кроме самого списка.

VM-only fresh raw captures лежат в
`/tmp/opencode/h1-final-review/current520/`: `directed-current.pkl.gz`
(412,696,630 bytes), `a-current.pkl.gz` (356,054,331 bytes), `range-current.json`,
`first-run.log`, `verification.log` и temporary freeze-control copy.
Большие `.pkl.gz` не входят в portable evidence.

Точная среда и команда выполненного replay:

```bash
export RESENSE_REPO=/tmp/opencode/h1-reviewed-publication
export PYTHONPATH="$RESENSE_REPO" PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export LD_LIBRARY_PATH=/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu
/tmp/opencode/resense-b4-venv/bin/python -B \
 "$RESENSE_REPO/docs/evidence/h1_current_source_2026-10-20/recheck_current.py"
```

Replay outputs эксклюзивны: существующие captures/reports не overwrite.
Для повторного full replay используйте отдельную копию driver с новыми `HERE`
и `WORK` внутри разрешённых evidence/scratch namespaces. Существующие результаты
можно повторно проверить без replay, выбрав новое имя verification output:

```bash
/tmp/opencode/resense-b4-venv/bin/python -B \
 "$RESENSE_REPO/docs/evidence/h1_current_source_2026-10-20/verify_current.py" \
 --out "$RESENSE_REPO/docs/evidence/h1_current_source_2026-10-20/verification-repeat.json"
```

Полные gate/X3/Falcon и G3 не запускались. Detector source, исходное evidence,
Git index/branches не редактировались; единственная runtime file installation —
разрешённая verified native.so copy. Коммитов/push/reseal не было.

**Итог: старые blocking H1 outputs точно воспроизведены на520e7dc. Изменение
lowobj.py не устранило63 misses и directed wrong-pair failures; H1 остаётся
BLOCKED / OPEN. Far-reference blocker также не снят.**
