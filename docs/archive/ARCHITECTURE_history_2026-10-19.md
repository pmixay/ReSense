# ARCHITECTURE: the 16.10 scope reconciliation, cut on 19.10.2026

> **Purpose:** two passages replaced in [`ARCHITECTURE.md`](../ARCHITECTURE.md) on 19.10 (documentation clean-up), word for word:
> the "Сверка scope 16.10" paragraph (H3/H4/H5 verdicts of the 1.1.0 package) and the seal paragraph. Statements such as "H6
> PENDING" and "в `main` — кандидат 1.2.0 (`aec88d2`, печать … 38 файлов)" are those of 16–18.10; the current state is in the live
> file. **Language:** RU · **Status:** archive

## Сверка scope 16.10

**Сверка scope 16.10:** выбранный runtime и исключённые S1/H1 — ниже. На точном `c9aea87`
[повторный H3](../evidence/integration_2026-10-16/h3_selected/README.md) — **PASS**: 208/208 строк
без задержек идентичны, 146 проверяемых строк пройдены, все 18 329 raw/serialized кадров
объяснены; [авторские пробы/dark](../evidence/integration_2026-10-16/h4_fixes/columns/WITHDRAWAL_RESULTS.md)
завершены. [Свежий независимый H4](../evidence/integration_2026-10-16/h4_selected/README.md)
принял пересмотренный scope: 306 passed, 36 граничных H2-проверок, 1 344 обновления трекера на
каждом исходнике, новых medium+ нет. Наследованный High-пропуск **OPEN 8.1**, исходный H4
**BLOCKED** сохранён. Полный [checkpoint](../evidence/integration_2026-10-16/README.md) разделяет
эти вердикты и историю. **H5 DONE:** [финальный шлюз 1.1.0](../evidence/integration_2026-10-16/h5/README.md)
на `5211565` после фиксации всех четырёх версий — **PASS**, 208/208 строк без задержек идентичны,
те же 146 проверяемых строк пройдены; все 18 329 raw/serialized кадров без нетайминговых изменений
относительно принятого `c9aea87`. [Текущая печать 16.10](../evidence/detector_freeze_2026-10-16_1.1.0.json)
создана из source/evidence-коммита `21e1d61`, записана в `d6319c2`; proof `ec81e78` — **PASS**
в чистом LF Linux checkout до и после сборки native. **H6 PENDING** (фактические CI/main);
пакет 1.1.0 выпускаться не будет (решение 19.10), опубликован v1.0.0; в `main` — кандидат 1.2.0 (`aec88d2`,
печать `detector_freeze_2026-10-18_b4_merged.json`, 38 файлов). Измерения 28–29.09 и 13.10 сохраняют свои версии;
новой оценки J1 нет.

## Печать детектора (абзац 18.10)

**Печать кандидата 1.2.0 — 18.10:** [`detector_freeze_2026-10-18_b4_merged.json`](../evidence/detector_freeze_2026-10-18_b4_merged.json),
38 файлов, digest `68dee667…` (проверка в чистом checkout:
[b4_merge_clean](../evidence/b4_merge_clean_2026-10-18/README.md)). **Печать 1.1.0 — 16.10 (не будет выпущен):** 36 файлов измеренного `5211565`, source/evidence-коммит
`21e1d61`, коммит манифеста `d6319c2`; digest
`db3f588df59184ad703436996f72bd94a91eca91dfcfe4a02655fcdd4397d751`.
[H5](../evidence/integration_2026-10-16/h5/README.md) хранит proof проверки явного нового манифеста
до/после native-сборки; [`DETECTOR_FREEZE.md`](../DETECTOR_FREEZE.md) описывает текущую печать.
