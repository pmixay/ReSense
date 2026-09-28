# Файл конфигурации

Вся настройка детектора — в одном файле,
[`configs/default.yaml`](https://github.com/pmixay/ReSense/blob/main/configs/default.yaml), под
корневым ключом `resense:`. CLI и нода ROS загружают один и тот же файл; в пакете ROS лежит его
копия (`ros2_ws/src/resense_ros/config/detector.yaml`), которая должна оставаться идентичной.

| раздел | что задаёт |
|---|---|
| `sensor` | соответствие осей (`forward: -y`, `left: +x`, `up: +z` для крепления организаторов), обрезка по дальности, фиксированный наклон крепления |
| `track` | модель пути: профиль полотна, шаблон пары рельсов (колея 1,52 м), подгонка по стенам для курсового угла и кривизны, до какой дальности доверять оси |
| `gauge` | габарит: `profile` (2,1 × 3,0 м организаторов, т. е. \|dy\| ≤ 1,05 м, 0,12–3,0 м над головкой рельса), `warning_margin` (зона предупреждения 0,35 м), дальность |
| `cluster` | DBSCAN с радиусом по дальности (`eps`, `range_scale`, `voxel`), фильтры и сигнатуры инфраструктуры |
| `tracking` | устойчивость до тревоги (`confirm_time_s`, `confirm_hits`, `conf_threshold`), удержания и оценка трека обученной моделью |
| `accumulation` | накопление кадров, только при известной скорости поезда |
| `lowobj` | низкие объекты на рельсах |
| `calibration` | автокалибровка крепления |
| `health` | проверки входа и оценка дальности контроля; они никогда не меняют обнаружение |

У каждого ключа в файле есть комментарий с датой и измерением, по которому выбрано значение.
Самые важные параметры и их влияние:
[`docs/ALGORITHM.md` §5](https://github.com/pmixay/ReSense/blob/main/docs/ALGORITHM.md#5-parameters-that-matter-most).

## Свой файл

Переданный файл накладывается на **значения по умолчанию из кода** в `resense/config.py`, а не на
`configs/default.yaml`, и неизвестный ключ — ошибка. Поэтому начинайте с полной копии:

```bash
cp configs/default.yaml my.yaml        # правьте my.yaml

resense run --bag <bag> --config my.yaml --out results.jsonl          # офлайн

docker run --rm -it --net=host --ipc=host -v $PWD/my.yaml:/cfg/my.yaml:ro resense \
  ros2 launch resense_ros detector.launch.py freshness_mode:=replay config_file:=/cfg/my.yaml   # нода
```

Крепление можно задать и на один запуск, без файла: аргументы запуска ноды `sensor_forward` /
`sensor_left` / `sensor_up` и `mount_*_deg` ([Параметры ноды](node-parameters.md)).

## Изменение значений по умолчанию (для разработчиков)

1. Отредактируйте `configs/default.yaml`.
2. `./scripts/sync_params.sh` копирует его в пакет ROS (с `--check` его запускает CI).
3. Изменение, которое влияет на обнаружение, проходит регрессионный гейт и получает новую печать
   детектора: [Изменение детектора](../development/detector-changes.md).
