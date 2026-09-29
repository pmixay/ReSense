# Показ на питче и репетиции

> **Назначение:** порядок живого показа на питче 23.10 (онлайн, демонстрация экрана), удалённый
> просмотр через Foxglove, запасной показ, что записывать на репетициях.
> **Аудитория:** капитан (ведёт питч и показ), команда · **Ответственный:** капитан (P1) с вечера 29.09 —
> P2 отказался от питча 29.09 вечером; интерфейс (дашборд, раскладки RViz и Foxglove) остаётся за P2
> · **Язык:** RU
> **Проверено:** 2026-09-29 вечер: команды сверены с [`README.md`](../README.md) «Кратко для жюри»,
> `docker-compose.yml` и [`docs/PRESENTATION.md`](../docs/PRESENTATION.md) «Демонстрация»; это сценарий,
> а не пройденная репетиция · **Статус:** текущий

Речь, слайды, вопросы жюри и репетиции — [`docs/PRESENTATION.md`](../docs/PRESENTATION.md); проверки
интерфейса — [`P2_REVIEW.md`](P2_REVIEW.md).

## Перед выступлением

```bash
sudo sysctl -w net.core.rmem_max=33554432                # буфер UDP для 360° облаков
docker load -i resense-image-<версия>.tar.gz             # или: docker build -t resense -f docker/Dockerfile .
cat /data/for_hackathon/doubleT_obstacle/*.db3 > /dev/null   # запись — в кэш диска (холодный диск срывал 120° на ВМ 28.09)
xhost +local:docker                                      # RViz из контейнера
```

Открыть заранее: окно для демонстрации экрана, плеер с
[`docs/video/docker_chain_rviz.mp4`](../docs/video/docker_chain_rviz.mp4), именную колоду.

## Показ (слайд 10, ~50 с)

```bash
# консоль 1: узел + RViz; ждать строку «ReSense detector listening on» (~0,7 с прогрева)
docker run --rm -it --net=host --ipc=host -e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix resense \
  ros2 launch resense_ros detector.launch.py rviz:=true freshness_mode:=replay
# консоль 2 (ROS 2 Humble на хосте): ограниченная очередь обязательна, иначе результаты устаревшие
ros2 bag play /data/for_hackathon/doubleT_obstacle --delay 3 --read-ahead-queue-size 10
# консоль 3 (по желанию): ros2 topic echo /resense/decision --field data
```

Без ROS 2 на хосте плеер — из образа: `RESENSE_DATA=/data/for_hackathon RESENSE_BAG=doubleT_obstacle
docker compose --profile tools up player`. Ожидается: в RViz коридор габарита, красная рамка и STOP
около 56 м в первые секунды; человек уходит — STOP держится на предмете у рельса до конца записи.
Это знакомая запись, не тест на новых данных. Узел в первые секунды догоняет стартовую пачку записи —
это нормально. Дашборд `web/index.html` в живом режиме требует rosbridge на хосте (`ws://localhost:9090`,
в образе его нет); без него — скриншот на слайде 10.

## Удалённый просмотр через Foxglove (по желанию)

```bash
RESENSE_DATA=/data/for_hackathon docker compose --profile viz up detector foxglove
RESENSE_DATA=/data/for_hackathon RESENSE_BAG=doubleT_obstacle docker compose --profile tools up player
```

Второе устройство в той же сети: Foxglove → Open connection → Foxglove WebSocket →
`ws://<адрес машины>:8765` → Layout → Import from file → `web/foxglove_layout.json`. По медленной сети
выключить только слой сырого облака. Индикаторы Foxglove показывают *последнее* значение (`LAST`) и не
гаснут: при обрыве смотреть соединение и свежесть `/resense/status`, старое GO не называть текущим.
Протокол моста: `python web/demo/check_foxglove_live.py --url ws://127.0.0.1:8765 --require-freshness`.

## Запасной показ

Нет решения через ~30 с после плеера или упал X11 — не чинить в эфире: показать
[`docs/video/docker_chain_rviz.mp4`](../docs/video/docker_chain_rviz.mp4) (69 с, STOP около 56 м на
0:24–0:30) и сказать, что это архивная запись той же цепочки (23.09), а не прогон текущего детектора.

## Репетиции

На каждой записать в [`P2_STATUS.md`](P2_STATUS.md) «Rehearsals»: дата, коммит и ID образа, время
(общее и по слайдам), STOP и дистанция в RViz, был ли переход на запасной ролик и сколько он занял.
Чек-лист — [`docs/PRESENTATION.md`](../docs/PRESENTATION.md) «Репетиции».

Именная колода (имена и фото на слайдах 2–3) собирается `scripts/build_deck.py --team`; команда
разрешила коммитить её вместо публичной, `team.json` и фото остаются вне git — команда сборки в
[`docs/PRESENTATION.md`](../docs/PRESENTATION.md) «Сборка колоды».
