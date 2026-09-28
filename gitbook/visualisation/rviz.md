# RViz

RViz показывает сырое облако, точки внутри коридора габарита, границы коридора, рамки препятствий
с расстоянием до них и текст состояния. Он запускается из того же образа; на хосте нужен дисплей
X11.

## Нода с RViz

Вместо обычной команды запуска ноды:

```bash
xhost +local:docker && docker run --rm -it --net=host --ipc=host \
  -e DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix \
  resense ros2 launch resense_ros detector.launch.py rviz:=true freshness_mode:=replay
```

Затем проиграйте бэг, как описано в разделе [Запуск на бэге](../getting-started/run-on-a-bag.md).

## Всё в одном контейнере

```bash
./scripts/run_demo.sh /data/for_hackathon/roundT_doubleT
```

Нода, RViz и плеер в одном контейнере (аргументы `bag:=` и `rviz:=true` launch-файла). Для
непрерывной демонстрации launch-файл принимает также `loop:=true`, `rate:=<factor>` и `delay:=<s>`.

## Через docker compose

```bash
xhost +local:docker
docker compose --profile viz up                 # детектор + RViz + мост Foxglove
docker compose --profile tools up player        # проигрывает $RESENSE_BAG
```

## Что видно

* **Фиксированная система координат (Fixed Frame) — `resense_lidar`.** Нода публикует статическое
  тождественное преобразование из `resense_lidar` в систему координат входного облака, поэтому одна
  и та же раскладка подходит для любого бэга.
* **Два дисплея сырого облака**, `/lidar_points` и `/sensing/lidar/hesai128/pointcloud`;
  отрисовывается тот, чей топик есть в бэге, второй остаётся серым с надписью
  «No messages received». Для бэга с третьим именем топика нужен ещё один дисплей
  (*Add → PointCloud2 →* выбрать топик); сама нода находит любой топик `PointCloud2`, поэтому
  обнаружения и коридор видны в любом случае.
* Цвета: сырое облако — оттенками серого по высоте, точки коридора — оранжевые, препятствия
  в габарите — красные, объекты зоны предупреждения — оранжевые, границы коридора — зелёные, текст
  состояния — над путём.
* Сохранённые виды на панели *Views*: *Top-down 150 m* и *Driver's seat*.

Файл раскладки — `ros2_ws/src/resense_ros/rviz/resense.rviz`; на хосте с ROS 2 его можно открыть
напрямую: `rviz2 -d ros2_ws/src/resense_ros/rviz/resense.rviz`.
