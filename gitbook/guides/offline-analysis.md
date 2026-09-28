# Офлайн-анализ без ROS

Детектор — обычная библиотека Python (`resense/`, numpy / scipy / scikit-learn, необязательные
ядра на C++). Команда `resense` запускает его прямо на каталоге бэга, без установки ROS.

## Установка

```bash
pip install -e ".[dev]"      # numpy scipy scikit-learn pyyaml + rosbags zstandard matplotlib open3d pytest
                             # ядра на C++ (native/) собираются, если есть компилятор
```

Без компилятора или с `RESENSE_NATIVE=0` работает путь на numpy: результат тот же, только
медленнее. `scripts/build_native.sh` собирает ядра без pip.

## Команды

```bash
resense info  /data/for_hackathon/roundT_doubleT                     # метаданные бэга и статистика первого кадра
resense run   --bag /data/for_hackathon/doubleT_obstacle --out results.jsonl --render out/   # JSON по каждому кадру + PNG на кадр
resense bench --bag /data/for_hackathon/roundT_doubleT --every 5     # время по этапам
resense summarize results.jsonl                                      # события тревоги, на час / км, задержка
```

Полезные опции `run`: `--every N` (каждый N-й кадр), `--start`, `--limit`, `--topic`,
`--config <yaml>` (другой файл параметров), `--ego-speed <m/s>` (известная скорость поезда
включает накопление по нескольким кадрам), `--quiet`. `--npy <dir>` читает кадры из кэша вместо бэга.

JSONL, который пишет `run --out`, — тот же покадровый результат, что нода публикует в
`/resense/status`; его можно загрузить в [веб-дашборд](../visualisation/web-dashboard.md) и проиграть.

![Кадр 20 записи doubleT_obstacle, как его рисует resense run --render: вверху вид сверху, внизу вид сбоку; серое — облако, жёлтое — точки внутри коридора габарита, зелёный пунктир — ось пути, синие рамки — предупреждения, красная — подтверждённое препятствие](../.gitbook/assets/render-top-side.png)

## Синтетические препятствия

Настоящие препятствия есть только в одной записи, поэтому положительные примеры на других
дальностях дают объекты, вписанные лучевым методом (ray casting) в реальные пустые кадры по
собственной схеме лучей сенсора:

```bash
resense inject --bag /data/for_hackathon/roundT_doubleT --every 10 --out data/synth \
               --distances 10:250 --kinds person,box,plank
resense eval data/synth                  # полнота (recall) по дальности на синтетическом наборе
```

`inject` также принимает `--placement bed|legacy`, `--sequence N --speed <m/s>` (объект,
приближающийся на протяжении N кадров) и `--augment`. Протокол оценочных наборов:
[`docs/EVALUATION.md`](https://github.com/pmixay/ReSense/blob/main/docs/EVALUATION.md).

## Оценка по разметке

```bash
resense eval --bag /data/for_hackathon/doubleT_obstacle --gt labels/doubleT_obstacle.json --repeat 1 --text
```

Формат разметки: [`docs/DATASET.md` «Формат разметки»](https://github.com/pmixay/ReSense/blob/main/docs/DATASET.md#формат-разметки-gtjson).
`web/label_tool.html` — инструмент в браузере, которым делается такая разметка.

## Сводка по реальным данным <a href="#the-real-data-report-card" id="the-real-data-report-card"></a>

Кадры один раз кэшируются, затем скрипты проходят по всем записям:

```bash
for b in /data/for_hackathon/*/; do
  python scripts/cache_frames.py $b /data/cache/$(basename $b) --every 1 --int16 --stamps
done
python scripts/eval_real.py --cache /data/cache --out out/eval       # ложные тревоги, размеченные человек / предмет, задержка
```

Единственная проверка результатов при изменениях детектора — регрессионный гейт: [Изменение
детектора](../development/detector-changes.md).
