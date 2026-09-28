# Foxglove (удалённая демонстрация)

Для зрителей, которые находятся не у машины, Foxglove заменяет удалённый рабочий стол: в образе уже
есть `foxglove_bridge`, а зрители открывают готовую раскладку в своём Foxglove (настольное
приложение или [app.foxglove.dev](https://app.foxglove.dev)).

## На демонстрационной машине

Бэги лежат в `$RESENSE_DATA` (по умолчанию `/data/for_hackathon`):

```bash
docker compose --profile viz up detector foxglove     # нода + мост на порту 8765
docker compose --profile tools up player              # проигрывает $RESENSE_BAG один раз
```

Для демонстрации по кругу добавьте `--loop` в команду плеера в `docker-compose.yml`.

## На каждом ноутбуке зрителя

1. Foxglove → **Open connection → Foxglove WebSocket → `ws://<demo host>:8765`**.
2. **Layout → Import from file →** [`web/foxglove_layout.json`](https://github.com/pmixay/ReSense/blob/main/web/foxglove_layout.json).

В раскладке есть панель 3D (камера за датчиком смотрит вдоль пути; оба топика сырого облака,
`/resense/corridor_points`, `/resense/markers`), индикатор `/resense/decision` (GO — зелёный,
CAUTION — оранжевый, STOP — красный, FAULT — фиолетовый), графики `nearest_distance`,
`clear_distance`, `latency_ms` и `fps` за последние 30 с и сырой JSON `/resense/status`.

## Проверка связи до подключения зрителей

```bash
pip install websockets
python web/demo/check_foxglove_live.py --url ws://127.0.0.1:8765 --require-freshness
```

Скрипт проверяет, что все топики раскладки объявлены и сообщения по ним приходят;
`--require-freshness` дополнительно требует актуальный `/resense/status`.

## По медленному каналу

Сырое облако — от 8 МБ (поле зрения 120°) до 24 МБ (360°) на кадр при 10 Гц. Снимите галочки
с двух топиков сырого облака на панели 3D и оставьте `/resense/corridor_points` (несколько тысяч
точек), маркеры и графики: это полная картина работы алгоритма при нескольких сотнях кБ/с.

## Известные ограничения

* Индикаторы показывают **последнее полученное** значение и никогда не считают его устаревшим:
  после обрыва связи на экране может остаться закэшированный GO или STOP. Проверяйте соединение
  и свежесть в `/resense/status` или используйте [веб-дашборд](web-dashboard.md), который сам
  помечает результаты устаревшими.
* Если после импорта панель пуста, заново выберите её топик в настройках панели. Панель 3D
  привязана к `resense_lidar` — статическому преобразованию ноды.
* Порт 8765 должен быть доступен зрителям; у моста нет аутентификации, поэтому открывайте его
  только в доверенной сети.
