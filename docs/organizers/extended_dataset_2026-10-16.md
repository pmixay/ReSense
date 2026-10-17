# Extended dataset and the second lidar — organizers' files of 16.10

> **Source:** organizers' chat, 16.10.2026 (relayed by the team). **Owner:** P1 (distribution), P4 (intake).
> **Status:** links and documents recorded 17.10; analysis in progress
> ([evidence/extended_data_2026-10-17/](../evidence/extended_data_2026-10-17/README.md),
> [sensor/falcon_prime/](../sensor/falcon_prime/README.md)).

## Messages (verbatim)

> Ольга Горбатова: А так же спецификация и User Manual на новый лидар, с которого будет дополнительный бэг из датасета
>
> Эксперты отправляют обещанные файлы
>
> https://disk.yandex.ru/d/DK6H3Lxiyi-M-Q
>
> Дополненный датасет
>
> https://disk.yandex.ru/d/SfBeRHbs8bNJAQ

These deliver what the experts' message of 16.10 announced ([`../FINALS_BRIEF_2026-10-16.md`](../FINALS_BRIEF_2026-10-16.md) §1):
extra synthetic data with similar clouds and extra obstacles (including a person and dust / suspension), and a real
recording from another lidar ("account for the different axis directions").

## Links and contents (Yandex Disk public API listing, 17.10)

| link | item | bytes | modified (UTC) | what it is |
|---|---|---:|---|---|
| [DK6H3Lxiyi-M-Q](https://disk.yandex.ru/d/DK6H3Lxiyi-M-Q) | `falcon_test.zst` | 6,758,209,772 | 2026-10-16 14:41 | real recording from the second lidar (Falcon Prime) |
| [SfBeRHbs8bNJAQ](https://disk.yandex.ru/d/SfBeRHbs8bNJAQ) (folder `bags`) | `falcon_test.zst` | 6,758,209,772 | 2026-10-16 14:41 | the same file as above |
| | `new_synth_data.zst` | 2,532,818,915 | 2026-10-16 18:43 | **new** synthetic set (person, dust / suspension per the experts' message) |
| | `cloud_with_fake_obj.zst` | 1,746,145,824 | 2026-09-24 13:07 | Set O, unchanged (same size and date as our intake, SHA-256 `d41c2fb2…`) |
| | `new_data.zst` | 17,078,961,996 | 2026-09-17 12:51 | the 20-minute ride, unchanged (same size and date) |

Download: `python scripts/unpack_dataset.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --member new_synth_data.zst --list`
(or `--member falcon_test.zst`); the script streams zstd → tar and writes only what is asked for.

## Second lidar documents (supplied with the message)

| file | what |
|---|---|
| [`../sensor/falcon_prime/Innovusion_Falcon-Prime-1_Datasheet_EN_Public_20230215.pdf`](../sensor/falcon_prime/Innovusion_Falcon-Prime-1_Datasheet_EN_Public_20230215.pdf) | datasheet (SHA-256 `8ffc005d…14fd`) |
| [`../sensor/falcon_prime/Seyond_Falcon_Prime_LiDAR_System_V1_0_2_English_public_20221214.pdf`](../sensor/falcon_prime/Seyond_Falcon_Prime_LiDAR_System_V1_0_2_English_public_20221214.pdf) | user manual, 56 pages (SHA-256 `a246e35d…08ac`) |
