# Где взять данные

Записи принадлежат организаторам и в репозиторий никогда не попадают. Все инструменты читают их
из смонтированного каталога или по переданному пути, по умолчанию `/data/for_hackathon`.

## Записи

| набор | что внутри | ссылка |
|---|---|---|
| шесть записей | по 20–88 с с разных участков метро, по одному топику; настоящие препятствия только в `doubleT_obstacle` (человек пересекает путь ≈ в 55–57 м впереди, предмет на правом рельсе) | `Датасет.zip`, 3,7 ГБ, [Google Drive](https://drive.google.com/file/d/1WTlR2wDSuEHTOARGK_gZeXDTZ9RZpswu/view) |
| `new_data` | 20-минутная поездка ~13 км без препятствий, разбита на 221 файл `.db3`, 90 ГБ в распакованном виде | `new_data.zst`, 17,1 ГБ, [Яндекс Диск](https://disk.yandex.ru/d/N8IUpAyd7jyvow) |
| `cloud_with_fake_obj` | 151 с, десять объектов, которые организаторы вписали лучевым методом (ray casting) в реальную запись | 1,75 ГБ, [Яндекс Диск](https://disk.yandex.ru/d/KpkG_yKoGk-vHQ) |

Размеры, число кадров, топики и сцены каждого бэга:
[`docs/DATASET.md`](https://github.com/pmixay/ReSense/blob/main/docs/DATASET.md).

## Распаковать только нужное

Архив вложенный (zip → zip → zstd tar). `scripts/unpack_dataset.py` читает его потоком и
записывает только запрошенные бэги (нужен `zstandard`, он входит в `pip install -e ".[dev]"`):

```bash
python scripts/unpack_dataset.py Датасет.zip --list
python scripts/unpack_dataset.py Датасет.zip --out /data --only doubleT_obstacle,roundT_doubleT
python scripts/unpack_dataset.py Датасет.zip --out /data                        # все шесть (~22 ГБ)
python scripts/unpack_dataset.py https://disk.yandex.ru/d/KpkG_yKoGk-vHQ --out /data   # cloud_with_fake_obj
```

Вручную: `tar --zstd -xf for_hackathon.zst -C /data` после двух распаковок zip.

Две записи, на которых CI проверяет холодный старт, можно скачать и сверить с зафиксированными
контрольными суммами через `scripts/fetch_cold_bags.sh <dir>` (скачивает, только если их ещё нет).

## Проверить новый бэг

```bash
resense info /data/for_hackathon/<bag>       # метаданные + первый кадр: топик, frame id, ширина, точки
resense run --bag /data/for_hackathon/<bag> --limit 30
```

Модель пути должна захватиться в первых кадрах, а пустой тоннель в начале не должен давать тревоги.
Если в выводе `track.center` скачет или `n_corridor` остаётся 0, соответствие осей сенсора
(`sensor.forward/left/up` или параметры ноды `sensor_forward/left/up`) не подходит к бэгу. Полный
порядок приёмки: [`docs/DATASET.md` «Как проверить новый бэг»](https://github.com/pmixay/ReSense/blob/main/docs/DATASET.md#как-проверить-новый-бэг-порядок-приёма).

## Монтирование данных в контейнеры

Скрипты монтируют родительский каталог бэга в `/data`; `docker compose` монтирует
`$RESENSE_DATA` (по умолчанию `/data/for_hackathon`) и проигрывает `$RESENSE_BAG`; обычному
`docker run` передаётся `-v <host dir>:/data:ro`.
