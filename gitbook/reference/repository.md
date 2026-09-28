# Карта репозитория и документы

## Структура

| путь | что там |
|---|---|
| `resense/` | основная библиотека (numpy / scipy / scikit-learn, без ROS): декодирование облаков точек, калибровка крепления, модель пути, коридор габарита, этап низких объектов, кластеризация, трекинг, исправность, детектор, вставка синтетических объектов, метрики, CLI `resense` |
| `native/` | необязательные ядра на C++ для самых нагруженных участков обработки кадра; запасной путь на numpy с идентичным результатом |
| `ros2_ws/src/resense_ros/` | нода ROS 2 Humble, launch-файл, копия параметров, раскладка RViz |
| `configs/default.yaml` | все параметры детектора |
| `docker/`, `docker-compose.yml` | образ и сервисы compose |
| `scripts/` | сборка, запуск, пробный прогон, экспорт / загрузка архива образа, оценка и регрессионный гейт |
| `web/` | веб-дашборд, раскладка Foxglove, инструмент разметки и их проверки без браузерного окна |
| `tests/` | набор тестов |
| `labels/` | разметка реальных препятствий и синтетических объектов организаторов |
| `docs/` | все документы; материалы организаторов — в `docs/organizers/` |
| `gitbook/` | эта книга |

## Документы в репозитории

| документ | зачем читать |
|---|---|
| [README](https://github.com/pmixay/ReSense/blob/main/README.md) | команды для жюри, текущий статус и главные результаты с датами |
| [ARCHITECTURE](https://github.com/pmixay/ReSense/blob/main/docs/ARCHITECTURE.md) | компоненты, поток данных, бюджет времени, ядра на C++, развёртывание без интернета |
| [ALGORITHM](https://github.com/pmixay/ReSense/blob/main/docs/ALGORITHM.md) | метод по этапам, правило решения, параметры, ограничения |
| [EXPERIMENTS](https://github.com/pmixay/ReSense/blob/main/docs/EXPERIMENTS.md) | все измерения: дальность, задержка, FPS, ложные тревоги, трудные случаи, что не сработало |
| [EVALUATION](https://github.com/pmixay/ReSense/blob/main/docs/EVALUATION.md) | протокол оценки и наборы данных |
| [DATASET](https://github.com/pmixay/ReSense/blob/main/docs/DATASET.md), [SENSOR](https://github.com/pmixay/ReSense/blob/main/docs/SENSOR.md) | записи, форматы, Hesai Pandar128 |
| [DECISIONS](https://github.com/pmixay/ReSense/blob/main/docs/DECISIONS.md) | ключевые решения на одной странице |
| [VM_GUIDE](https://github.com/pmixay/ReSense/blob/main/docs/VM_GUIDE.md) | пробный прогон на чистой машине, замеры производительности и репетиция без интернета на облачной ВМ |
| [CHANGELOG](https://github.com/pmixay/ReSense/blob/main/CHANGELOG.md) | что изменилось — по версиям и слияниям |
| [docs/README](https://github.com/pmixay/ReSense/blob/main/docs/README.md) | указатель всех документов: назначение и ответственный |

Спецификация организаторов и их ответы:
[`docs/organizers/`](https://github.com/pmixay/ReSense/tree/main/docs/organizers).
