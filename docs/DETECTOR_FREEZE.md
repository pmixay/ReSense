# Заморозка детектора

> **Назначение:** что опечатано, как проверяется печать, шлюз, который её подтверждает, и как будет
> приниматься изменение детектора.
> **Аудитория:** команда, жюри · **Ответственный:** P1 (печать), P3 (детектор) · **Язык:** RU
> **Проверено:** 2026-09-29: `python3 scripts/detector_freeze.py verify` PASS; охват манифеста, шлюз и
> базовая линия — по `scripts/detector_freeze.py`; повторный прогон шлюза от 28.09 ·
> **Статус:** актуален; детектор опечатан и не меняется до сдачи

## Что опечатано

Детектор цикла качества 27.09 (детектор `352ca13`, измерен на `d572807`), опечатанный файлом
[`detector_freeze_2026-09-27.json`](evidence/detector_freeze_2026-09-27.json): SHA-256 его 31 файла в
`resense/` (включая обученную оценку трека `resense/models/track_opinion.json`), `native/`, `configs/`,
`ros2_ws/src/resense_ros/config/` и входов сборки `setup.py`, `pyproject.toml`,
`scripts/build_native.sh`; хеши конфигурации, измеренный коммит, а также подтверждающий шлюз и его
базовая линия — по пути и хешу. Код ноды ROS, launch-файл, Docker, CI и документы лежат вне печати и
имеют собственные проверки.

## Как проверить

`python3 scripts/detector_freeze.py verify` (только стандартная библиотека; без данных, пакетов и
клона Git) завершается ошибкой, если опечатанный файл добавлен, изменён или удалён, если
`configs/default.yaml` и его копия для ROS различаются, или если шлюз либо базовая линия (baseline),
названные в манифесте, изменились или больше не фиксируют полный, пройденный шлюз без послаблений
(waivers). CI запускает его в задании `checks` при каждом пуше. Он не прогоняет никаких данных, и
файл, заменённый вместе с записанным хешем, проходит проверку: изменение манифеста ревьюится как код.

## Шлюз, подтверждающий печать

[`regression_gate_2026-09-27_quality.json`](evidence/results/regression_gate_2026-09-27_quality.json):
каждый кадр шести записей, набора O, всей поездки и набора F straight на конфигурации по умолчанию,
против [`regression_baseline_2026-09-26_ride_p3d.json`](evidence/results/regression_baseline_2026-09-26_ride_p3d.json):
PASS без `--allow`, без отсутствующих строк и без ухудшившихся проверяемых метрик. Этот же прогон
служит текущей базовой линией
[`regression_baseline_2026-09-27_quality.json`](evidence/results/regression_baseline_2026-09-27_quality.json);
повторный прогон против неё на ВМ команды 28.09 дал тот же результат, кроме информационных строк
задержки ([`gate_2026-09-28/`](evidence/gate_2026-09-28/gate_table.txt)). Независимые выходные данные
по кадрам: [`judge_outputs_2026-09-28/`](evidence/judge_outputs_2026-09-28/README.md),
[`judgement_2026-09-28/`](evidence/judgement_2026-09-28/README.md). Измеренное качество и
ограничения: [`SCORECARD.md`](SCORECARD.md), `docs/EXPERIMENTS.md`. Печать — это запись о
целостности, а не релиз, не одобрение развёртывания и не доказательство безопасности.

## Как будет принято изменение

До сдачи изменений не планируется. После неё изменение детектора требует, по порядку:

1. дефект и его приёмочный тест, закоммиченные до любого запуска; патч, прошедший ревью;
   проходящие затронутые тесты; закоммиченный детектор;
2. **полный шлюз** на этом коммите (конфигурация по умолчанию, поездка и набор F в кэше, как в
   [`VM_GUIDE.md`](VM_GUIDE.md) §2.3): код выхода 0, каждая проверяемая метрика такая же или лучше,
   без `--allow`; изменение, которое должно сдвинуть числа, коммитит вместе с собой новую базовую
   линию;
3. **независимое ревью безопасности** патча и его отличий по кадрам: ни один STOP не потерян, не
   задержан и не укорочен на наборе O, реальном препятствии, случаях дальности и стресс-прогонах;
4. **новую печать (reseal)**, прошедшую ревью: `create` отказывается работать с шлюзом с
   послаблениями, отсутствующими строками или переопределениями, а также с опечатываемым файлом,
   который отличается от измеренного коммита; затем `DEFAULT_MANIFEST` в
   `scripts/detector_freeze.py` указывает на новый манифест, и `verify` проходит.

```bash
python scripts/regression_gate.py --cache /data/cache --jobs 4 \
  --baseline docs/evidence/results/regression_baseline_2026-09-27_quality.json \
  --out docs/evidence/results/regression_gate_<date>_<change>.json
python scripts/detector_freeze.py create --manifest docs/evidence/detector_freeze_<date>.json \
  --baseline docs/evidence/results/regression_baseline_2026-09-27_quality.json \
  --evidence docs/evidence/results/regression_gate_<date>_<change>.json
```

Замещённые печати P3d от 26.09: [`detector_freeze_2026-09-26.json`](evidence/detector_freeze_2026-09-26.json),
[`…_before_comment_correction.json`](evidence/detector_freeze_2026-09-26_before_comment_correction.json).
Как появился опечатанный детектор: [`archive/QUALITY_CYCLE_2026-09-27.md`](archive/QUALITY_CYCLE_2026-09-27.md).
