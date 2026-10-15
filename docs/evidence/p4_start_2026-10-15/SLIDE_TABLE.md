# PT1 handoff: robustness on v1.0.0

| input | platform false episodes | obstacle STOP | Set O inside hits |
|---|---:|---:|---:|
| nominal | 3 | 193/201 | 424/801 |
| pitch +2° | 4 | 192/201 | 414/801 |
| pitch −2° | 7 | 193/201 | 425/801 |
| roll +2° | 7 | 192/201 | 420/801 |
| 5 Hz | 9 | 95/101 | 200/401 |
| dropout 30%, seed 7 | 14 | 154/201 | 403/801 |
| dedup | 3 | 189/201 | 406/801 |

Exact `707ea9c`; judge figures reproduced exactly. RoundT-squareT: zero.
40 cases, jobs 2, 18:16 on shared Windows. Development-data robustness,
not held-out validation. Per-object/outside metrics: [report](README.md).
