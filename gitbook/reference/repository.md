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
| `webapp/` | [веб-прототип](../visualisation/web-prototype.md) для жюри, вне релиза и образа: бэкенд FastAPI `resense-web` (`webapp/backend`), фронтенд React + TypeScript + Vite (`webapp/frontend`), контракт HTTP (`webapp/API.md`), браузерные тесты (`webapp/e2e`), макет дизайна (`webapp/design/mockup`); запуск — `scripts/run_webapp.sh` |
| `tests/` | набор тестов |
| `labels/` | разметка реальных препятствий и синтетических объектов организаторов |
| `docs/` | все документы; материалы организаторов — в `docs/organizers/`, доказательства (сырые данные замеров) — в `docs/evidence/`, датированные записи — в `docs/archive/` |
| `gitbook/` | эта книга |

## Документы в репозитории

| документ | зачем читать |
|---|---|
| [README](https://github.com/pmixay/ReSense/blob/main/README.md) | команды для жюри, главные результаты и ограничения |
| [SCORECARD](https://github.com/pmixay/ReSense/blob/main/docs/SCORECARD.md) | независимая оценка 28.09 (детектор до изменений 29.09): как измеряли, результаты по каждой записи, главные риски |
| [ARCHITECTURE](https://github.com/pmixay/ReSense/blob/main/docs/ARCHITECTURE.md) | компоненты, поток данных, бюджет времени, ядра на C++, развёртывание без интернета |
| [ALGORITHM](https://github.com/pmixay/ReSense/blob/main/docs/ALGORITHM.md) | метод по этапам, правило решения, параметры, ограничения |
| [EXPERIMENTS](https://github.com/pmixay/ReSense/blob/main/docs/EXPERIMENTS.md) | измерения: дальность, задержка, FPS, ложные тревоги, трудные случаи, что не сработало |
| [EVALUATION](https://github.com/pmixay/ReSense/blob/main/docs/EVALUATION.md) | протокол оценки и наборы данных |
| [DATASET](https://github.com/pmixay/ReSense/blob/main/docs/DATASET.md), [SENSOR](https://github.com/pmixay/ReSense/blob/main/docs/SENSOR.md) | записи, форматы, Hesai Pandar128 |
| [DECISIONS](https://github.com/pmixay/ReSense/blob/main/docs/DECISIONS.md), [RESEARCH](https://github.com/pmixay/ReSense/blob/main/docs/RESEARCH.md) | ключевые решения на одной странице; обзор литературы и рассмотренные подходы |
| [DETECTOR_FREEZE](https://github.com/pmixay/ReSense/blob/main/docs/DETECTOR_FREEZE.md) | печать детектора (текущая — 29.09 ночь, после выключения `shell`, `7464d80`) и её проверка |
| [VM_GUIDE](https://github.com/pmixay/ReSense/blob/main/docs/VM_GUIDE.md) | пробный прогон на чистой машине, замеры производительности и репетиция без интернета на облачной ВМ |
| [CHANGELOG](https://github.com/pmixay/ReSense/blob/main/CHANGELOG.md) | что изменилось — по версиям |
| [webapp/README](https://github.com/pmixay/ReSense/blob/main/webapp/README.md), [webapp/API](https://github.com/pmixay/ReSense/blob/main/webapp/API.md) | веб-прототип: запуск, страницы, архитектура, тесты; HTTP-контракт бэкенда и фронтенда |
| [docs/archive/](https://github.com/pmixay/ReSense/tree/main/docs/archive) | датированные записи: полный журнал экспериментов, подробный журнал изменений, циклы качества |
| [docs/video/](https://github.com/pmixay/ReSense/tree/main/docs/video), [docs/presentation/](https://github.com/pmixay/ReSense/tree/main/docs/presentation) | обзорное видео и ролики, презентация (отвечает P2) |
| [docs/README](https://github.com/pmixay/ReSense/blob/main/docs/README.md) | указатель всех документов: назначение и ответственный |

Спецификация организаторов и их ответы:
[`docs/organizers/`](https://github.com/pmixay/ReSense/tree/main/docs/organizers).
