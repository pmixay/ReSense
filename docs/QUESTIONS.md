# Вопросы организаторам (кейс 05, команда ReSense)

Owner: P1 (captain). Sprint 0 item 4 of [`CAPTAIN.md`](CAPTAIN.md) plus the sensor questions from
[`SENSOR.md`](SENSOR.md) §4. The text below is ready to send as one message to the case moderator
(Telegram [@gorbatovaol](https://t.me/gorbatovaol)) or to info.leaders@develop.mos.ru; the
English notes after each block say why we ask and where the answer goes. Record the answers in
[`DATASET.md`](DATASET.md) (data), [`SUBMISSION.md`](SUBMISSION.md) (submission), [`SENSOR.md`](SENSOR.md)
(sensor) and mark the question here as answered.

Status: **drafted 21.09, not yet sent** — the captain sends it and updates this file.

---

Здравствуйте! Команда ReSense, кейс 05 (посторонние объекты в тоннеле метро по 3D-лидару).
Мы прошли по выданным шести bag-файлам и хотим уточнить несколько вещей, чтобы решение
запускалось у вас на стенде с первого раза и не было подогнано под конкретные записи.
Если получится ответить только на часть — самые важные для нас **1, 2, 6, 7 и 9**.

**Данные и контрольная запись**

1. Расширенный датасет с препятствиями: будет ли он, когда, сколько записей, и будут ли
   размечены препятствия (тип объекта, расстояние, положение относительно пути)? В каком
   формате разметка? В выданных записях внутри габарита препятствий нет (только человек,
   переходящий путь в `doubleT_obstacle`), поэтому пока все положительные примеры у нас
   синтетические.
   *(22.09: получена ссылка на `new_data.zst` — одна непрерывная запись ~19 мин, см.
   `DATASET.md` «Extended dataset». Уточняющий вопрос: есть ли в ней постановочные
   препятствия — какие объекты, на каких секундах записи / в каких файлах `new_data_<N>.db3`
   и на каком расстоянии; или это только фон для оценки ложных срабатываний?)*
2. Контрольный bag-файл: какой топик и `frame_id` у облака? В выданных записях два варианта —
   `/lidar_points` + `hesai_lidar` (окно 120°, 1200 столбцов) и
   `/sensing/lidar/hesai128/pointcloud` + `lidar_livox` (полный оборот 360°). Будет ли в
   контрольной записи тот же лидар, та же установка и то же азимутальное окно? Формат
   хранения — sqlite3, как сейчас, или mcap?
3. Лидар: подтвердите, пожалуйста, модель (по данным похоже на Hesai Pandar128 E3X), режим
   возврата (dual: last + strongest?), высоту и наклон установки на поезде и смещение
   относительно оси пути. В выданных записях два разных крепления (полотно на 1.5 м и на
   2.0 м ниже сенсора) — мы самокалибруемся по рельсам, но число поможет для синтетики.
4. Синхронизация и движение: будет ли на поезде PTP/GNSS-время (сейчас поле `timestamp`
   в точках — эпоха 2000 года, т.е. не синхронизировано)? Будет ли в записи скорость поезда,
   одометрия или IMU (топик и тип сообщения)? Это нужно для накопления кадров на 150–300 м.
5. Сценарии контрольных данных: движется ли поезд и с какой скоростью; какие препятствия
   ожидаются (человек, ящик, инструмент, тележка, …) и на каких дальностях; будут ли станции,
   стрелки, гермозатворы; считается ли препятствием человек на платформе или рядом с путём
   вне габарита?

**Сдача и проверка**

6. Промежуточная сдача: дата, обязательна ли она, в каком виде (ссылка на репозиторий,
   архив, Docker-образ) и куда загружать.
7. Финальная сдача: достаточно ли Dockerfile в репозитории или нужен готовый образ
   (`docker save`)? Есть ли ограничение по размеру? Требования к видео (длительность,
   формат, где размещать — в репозитории или ссылкой)?
8. Стенд проверки: как именно будет запускаться решение — по README вручную? Есть ли
   доступ в интернет при сборке образа (apt/pip)? Будет ли доступен GPU из контейнера
   (nvidia-container-toolkit) — мы его не используем, но хотим знать, что не нужно?
   Как проигрывается bag — `ros2 bag play` на хосте с `--clock` или внутри контейнера?
   (Состояние драйвера и CUDA на стенде нам сообщили 22.09 — записано в
   [`organizers/test_stand_software.md`](organizers/test_stand_software.md); открытыми
   остаются порядок запуска, доступ в интернет при сборке и способ проигрывания bag.)
9. Как оценивается результат: по топикам (какие сообщения удобнее вашему пайплайну —
   `vision_msgs/Detection3DArray`, флаг + расстояние, свой тип), по логам или по
   визуализации? Как измеряются дальность обнаружения и ложные срабатывания — по кадрам,
   по событиям, по времени? В какой системе координат ожидается положение препятствия?
10. Допустимо ли использовать выданные записи для настройки параметров (мы считаем это
    нормальным, но хотим убедиться, что это не расценивается как «подгонка»)?

**Демонстрация**

11. Демонстрация в реальном времени через удалённый рабочий стол: чей стенд и какая
    платформа (наш экран через Zoom/Meet, или доступ к вашему стенду)? Сколько минут на
    выступление и демо?
12. Презентация: слайды 7–11 по шаблону обязательны — можно ли добавлять свои слайды после
    них, и в каком формате сдавать (pptx / pdf)?

Спасибо!

---

## Why each question matters (for the team)

| # | answer goes to | consequence for the code / plan |
|---|---|---|
| 1 | `DATASET.md` §"extended dataset", P4 labelling | decides whether real recall numbers exist by 29.09 or synthetic stays the only positive set |
| 2 | `DATASET.md` "Topic and sensor", `detector_node.py` defaults | the node auto-discovers PointCloud2 topics and the RViz layout must not hard-code the frame; a confirmed name lets us pin it |
| 3 | `SENSOR.md` §1–2, `resense/sensor.py`, `resense inject` | mount height/pitch calibrates the synthetic injector and the expected-point prior |
| 4 | `SENSOR.md` §4, P3 accumulation, node `ego_speed` hook | with a speed/odometry topic the accumulation stage needs no ICP; without it we estimate speed from the bed/walls |
| 5 | `EVALUATION.md` §1 (set H), `EXPERIMENTS.md` hard cases | tells P3 which false-alarm classes to prioritise (platforms vs gates vs curves) |
| 6–7 | `SUBMISSION.md` | tag date, whether to `docker save`, video hosting |
| 8 | `docker/Dockerfile`, `scripts/run_demo.sh` | offline build would need vendored wheels/apt cache; `--clock` decides `use_sim_time` handling |
| 9 | `detector_node.py` topics (frozen contract in `CAPTAIN.md` §2) | add a message type if they name one; never rename the existing topics |
| 10 | — | how much of the six bags P3 may use for tuning vs holding out |
| 11–12 | `PRESENTATION.md`, README "remote demo" runbook | Foxglove-bridge path vs screen share |
