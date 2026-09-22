# Вопросы организаторам (кейс 05, команда ReSense)

Owner: P1 (captain). Sprint 0 item 4 of [`CAPTAIN.md`](CAPTAIN.md) plus the sensor questions from
[`SENSOR.md`](SENSOR.md) §4. The text below is ready to send as one message to the case moderator
(Telegram [@gorbatovaol](https://t.me/gorbatovaol)) or to info.leaders@develop.mos.ru; the
English notes after each block say why we ask and where the answer goes. Record the answers in
[`DATASET.md`](DATASET.md) (data), [`SUBMISSION.md`](SUBMISSION.md) (submission), [`SENSOR.md`](SENSOR.md)
(sensor) and move the question to the "Closed" table at the end of this file.

Status: **drafted 21.09, revised 22.09 after the organizers' hand-outs (lidar manual, test-stand
software, extended recording — see "Closed" below), not yet sent** — the captain sends it and
updates this file.

---

Здравствуйте! Команда ReSense, кейс 05 (посторонние объекты в тоннеле метро по 3D-лидару).
Спасибо за руководство по лидару, данные о стенде и новую запись `new_data` — мы их
разобрали. Осталось несколько вопросов, чтобы решение запускалось у вас на стенде с первого
раза и не было подогнано под конкретные записи. Если получится ответить только на часть —
самые важные для нас **1, 2, 6, 7 и 9**.

**Данные и контрольная запись**

1. Запись `new_data` (20 минут, 221 файл): есть ли в ней постановочные препятствия? Если да —
   какие объекты, в каких файлах `new_data_<N>.db3` / на каких секундах записи и на каком
   расстоянии они появляются; будет ли разметка и в каком формате? Если это только фон
   (поездка без препятствий) — планируется ли запись с препятствиями до контрольной? В
   выданных записях внутри габарита препятствий нет (только человек, переходящий путь в
   `doubleT_obstacle`), поэтому пока все положительные примеры у нас синтетические.
2. Контрольная запись: верно ли, что она будет такой же, как `new_data` и пять из шести первых
   записей — топик `/lidar_points`, `frame_id` `hesai_lidar`, окно 120° (1200 столбцов),
   хранение sqlite3 (при необходимости разбитое на файлы)? Одна из выданных записей
   (`doubleT_obstacle`) отличается: `/sensing/lidar/hesai128/pointcloud`, `lidar_livox`,
   полный оборот 360° — стоит ли ожидать и такой вариант?
3. Настройки лидара и установка: какой режим возврата включён в записях — по данным
   (дублирующиеся точки у лучей с одним отражением) похоже на dual *Last and First*, хотя по
   умолчанию у Pandar128 *Last and Strongest*; будет ли контрольная запись в том же режиме
   (High Resolution, 0.1°, то же окно)? Какова высота и наклон установки на поезде и смещение
   относительно оси пути? В выданных записях два разных крепления (полотно на 1.5 м и на
   2.0 м ниже сенсора) — мы самокалибруемся по рельсам, но число поможет для синтетики.
4. Синхронизация и движение: будет ли на поезде PTP/GNSS-время (во всех записях, включая
   `new_data`, поле `timestamp` в точках — эпоха 2000 года, т.е. не синхронизировано)? Будет
   ли в записи скорость поезда или одометрия (топик и тип сообщения)? Pandar128 передаёт в
   каждом пакете данные встроенного IMU — публикует ли ваш драйвер их отдельным топиком?
   Это нужно для накопления кадров на 150–300 м.
5. Сценарии контрольных данных: `new_data` — это поездка с семью остановками, станциями,
   стрелкой и кривыми; контрольная запись будет похожей? Какие препятствия ожидаются
   (человек, ящик, инструмент, тележка, …) и на каких дальностях; считается ли препятствием
   человек на платформе или рядом с путём вне габарита?

**Сдача и проверка**

6. Промежуточная сдача: дата, обязательна ли она, в каком виде (ссылка на репозиторий,
   архив, Docker-образ) и куда загружать.
7. Финальная сдача: достаточно ли Dockerfile в репозитории или нужен готовый образ
   (`docker save`)? Есть ли ограничение по размеру? Требования к видео (длительность,
   формат, где размещать — в репозитории или ссылкой)?
8. Стенд проверки: как именно будет запускаться решение — по README вручную? Есть ли
   доступ в интернет при сборке образа (apt/pip)? Как проигрывается bag — `ros2 bag play`
   на хосте с `--clock` или внутри контейнера? Будет ли на стенде место под распакованную
   `new_data` (90 ГБ), если контрольная запись такого же объёма?
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
| 1 | `DATASET.md` "Extended dataset", `labels/`, P4 labelling | decides whether real recall numbers exist by 29.09 or synthetic stays the only positive set; the 102 v0.5 events on `new_data` are false alarms only if nothing was staged |
| 2 | `DATASET.md` "Topic and sensor", `detector_node.py` defaults | the node auto-discovers PointCloud2 topics and the RViz layout must not hard-code the frame; a confirmed name lets us pin it |
| 3 | `SENSOR.md` §2 (dual return, defaults), `resense/sensor.py`, `resense inject` | return mode decides how duplicates are merged and the point budget; mount height/pitch calibrates the synthetic injector and the expected-point prior |
| 4 | `SENSOR.md` §4, P3 accumulation, node `ego_speed` / `odom_topic` hook | with a speed/odometry topic the accumulation stage needs no ICP; an IMU topic would give pitch/vibration compensation for free |
| 5 | `EVALUATION.md` §1 (set H), `EXPERIMENTS.md` hard cases | tells P3 which false-alarm classes to prioritise (platforms vs gates vs curves) |
| 6–7 | `SUBMISSION.md` | tag date, whether to `docker save`, video hosting |
| 8 | `docker/Dockerfile`, `scripts/run_demo.sh`, `dry_run.sh` | offline build would need vendored wheels/apt cache; `--clock` decides `use_sim_time` handling; disk decides whether the dry run can use `new_data` |
| 9 | `detector_node.py` topics (frozen contract in `CAPTAIN.md` §2) | add a message type if they name one; never rename the existing topics |
| 10 | — | how much of the six bags P3 may use for tuning vs holding out |
| 11–12 | `PRESENTATION.md`, README "remote demo" runbook | Foxglove-bridge path vs screen share |

## Closed by the organizers' hand-outs (22.09)

| was asked | what came | recorded in |
|---|---|---|
| lidar model and specifications (old item 3) | the Pandar128E3X user manual (Hesai doc 128-en-240710): model confirmed, every number re-checked | [`SENSOR.md`](SENSOR.md), the PDF in [`sensor/`](sensor/) |
| will there be an extended dataset, when, how many recordings (old item 1) | `new_data.zst`: one 20-minute recording, 221 split files, no labels | [`DATASET.md`](DATASET.md) "Extended dataset", `extended_dataset_intake.json` |
| GPU / CUDA on the test stand (old item 8, in part) | `nvidia-smi` and `dpkg` state of the stand (driver 580, CUDA 13 runtime, toolkit 12.9); ReSense does not use it | [`organizers/test_stand_software.md`](organizers/test_stand_software.md) |
