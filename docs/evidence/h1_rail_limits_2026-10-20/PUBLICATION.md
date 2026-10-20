# H1 rail evidence: compact publication

Эта упаковка сохраняет уже измеренный evidence; detector replay и новые
эксперименты при публикации **не запускались**. Measured HEAD остаётся
`f56ad5e62d9d051811c804734c7731b6951eae90`; исходные measured receipts не
переименованы в результаты текущего HEAD. Изменения production/Git index/HEAD
во время упаковки проверены отдельно в `publication-manifest.json`.

## Что публиковать

**Точный allowlist:** `publication-manifest.json:exact_allowlist`.
Имена относительно `docs/evidence/h1_rail_limits_2026-10-20/`.
Только этот список является публикационным набором; исходные большие файлы
остаются на ВМ и отдельно в GitHub не дублируются.

В набор входят README/protocol/acceptance-plan, этот документ, maintained
evidence `.py` tools, `raw-examples.png`, `ACCEPTANCE.json`, небольшие final
receipts/manifests и архив. Every-case outputs, exploratory outputs, полные
raw NPZ, source snapshot, snapshots и logs доступны через архив.

## Полный portable archive

| Поле | Значение |
|---|---|
| Файл | `raw-evidence.tar.xz` |
| Размер | **18,559,004 bytes** (17.699 MiB) |
| SHA-256 | `cd728d5bef1e68b16263621416f3eddad6471f49e272eea3de8e1daa442c45b9` |
| Исходные файлы | **128**, суммарно **84,593,775 bytes** |
| Формат | tar + xz/LZMA2 preset 9 extreme, CRC64 |
| Имена members | Exact original filenames в корне архива, без дополнительного directory prefix |

В архив включены **все исходные generated JSON/NPZ, source tar, logs**, все
исторические evidence tools/documents/image и исходный `SHA256SUMS`.
Ни `__pycache__`, ни `.pyc` в нём нет. Содержимое файлов не преобразовано;
tar metadata нормализованы (mode 0644, mtime 0), payload bytes сохранены точно.
Логические subsets не понадобились: полный архив меньше 20 MB.

`publication-manifest.json:archive.members` содержит размер и SHA-256 **каждого
исходного member**. После записи все 128 members повторно открыты, их bytes
сравнены с исходными файлами, размер и SHA-256 сверены. Отдельный verifier
проверяет распаковку через GNU tar и все restored files через внешний
`sha256sum` — без запуска detector.

## Два набора checksums и README

* **Исторический** `SHA256SUMS` сохранён неизменным в архиве и на ВМ: 127
  записей с исходными абсолютными путями. Сам файл тоже имеет member hash.
  `artifact-manifest.json` — сохранённый исторический manifest, не манифест
  текущего публикационного allowlist. Их содержимое не исправлялось.
* **Публикационный** `SHA256SUMS-publication` содержит portable relative paths,
  hashes файлов allowlist, включая `publication-manifest.json`; исключает
  только свой собственный checksum, чтобы избежать цикла.
* В публикуемом `README.md` удалена приватная SSH-строка и добавлена ссылка на
  этот документ. Исторические measured receipts не санитизировались и не
  перезаписывались.
* Исходный `README.md` восстановим из archive member **`README.md`**:
  **18,007 bytes**, SHA-256
  `05ab29218c8d73ba4a2e0b8018bbc76a7a441139bea0c5068a3d71bd314365cc`.
  Published README имеет отдельный hash в `publication-manifest.json` и
  `SHA256SUMS-publication`. Поэтому historical checksum README ожидаемо
  отличается от публикационного; это документированная редакция упаковки.

## Проверка публикации без replay

Из этого evidence directory, стандартным Python 3:

```bash
sha256sum -c SHA256SUMS-publication
python3 -B h1_verify_publication.py
```

Verifier проверяет все publication payloads, 128 archive members, все 127
исторических checksum records и различие двух версий README. Positive control
принимает known original README hash и обнаруживает изменённый hex nibble.
Он не импортирует detector, NumPy/SciPy или evidence replay scripts.

Для независимой GNU tar extraction verification указать **новый** directory
под уже существующим temp parent:

```bash
python3 -B h1_verify_publication.py --extract-check /existing/temp-parent/h1-review
```

Это выполняет `xz --test`, GNU tar list/extraction, проверяет exact filename
set и SHA-256 каждого restored original внешним `sha256sum`. Detector также
не запускается. В предоставленном проверочном запуске использовался отдельный
scratch directory, а исходные файлы на ВМ сохранены.

## Восстановление для reviewer scripts

Распаковать архив в отдельный review directory, передав его как `-C`:

```bash
tar -xJf raw-evidence.tar.xz -C /existing/review-directory
```

Там появятся **исходные filenames на одном уровне**: `<case>.json`,
`raw_*.npz`, `components.json`, `independent-check-complete.json`,
`source.tar.gz`, `h1_verify.py` и остальные tools. Их `HERE` снова указывает
на папку с ожидаемыми inputs. Это restore payload, а не новый capture.
Зависимости и исходный detector для возможной последующей предметной проверки
описаны в историческом README и measured source/runtime receipts.

При extraction непосредственно в публикационный evidence directory archive
восстановит и **исторический README**, заменив публикационную редакцию.
Для одновременного сохранения двух представлений использовать отдельный review
directory. Старый абсолютный `SHA256SUMS` не следует исполнять как portable
checksum command в другом checkout: verifier проверяет его исходные records
по basename и member hashes, не меняя оригинальных bytes.

## Инструменты упаковки

`h1_publish.py prepare` был выполнен до изменения README: он сверил
исторические checksums, собрал xz archive, reopened/byte-compared members,
сохранил original README в разрешённом temp parent. `finish` формирует
allowlist и новые publication receipts после редакции README; старые receipts
не меняет. Этот capture-specific builder не требуется reviewer и отказывается
перезаписывать существующие publication artifacts.

Полный inventory, размеры, hashes и scope checks — в
`publication-manifest.json`. В этой работе staging, commit, push или иные
Git changes не выполнялись.
