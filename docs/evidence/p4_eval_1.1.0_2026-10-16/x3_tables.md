| variant | squareT false episodes (STOP frames) | obstacle STOP / processed | roundT-squareT false episodes | Set O inside matched / visible rows | Set O outside false frames / episodes | Set O unmatched frames / episodes |
|---|---:|---:|---:|---:|---:|---:|
| nominal | 3 (11) | 193/201 | 0 | 424/801 | 9 / 1 | 6 / 6 |
| pitch +2° | 4 (20) | 192/201 | 0 | 414/801 | 12 / 2 | 6 / 6 |
| pitch −2° | 7 (27) | 193/201 | 0 | 425/801 | 7 / 1 | 6 / 6 |
| roll +2° | 7 (37) | 192/201 | 0 | 420/801 | 9 / 1 | 7 / 7 |
| 5 Hz | 9 (19) | 95/101 | 0 | 200/401 | 0 / 0 | 8 / 8 |
| dropout 30%, seed 1 | 12 (56) | 178/201 | 0 | 403/801 | 6 / 1 | 10 / 8 |
| dropout 30%, seed 2 | 10 (55) | 178/201 | 0 | 410/801 | 8 / 1 | 9 / 8 |
| dropout 30%, seed 3 | 13 (51) | 178/201 | 0 | 407/801 | 7 / 1 | 6 / 6 |
| dropout 30%, judge seed 7 | 14 (61) | 154/201 | 0 | 403/801 | 0 / 0 | 9 / 8 |
| dedup | 3 (20) | 189/201 | 0 | 406/801 | 8 / 1 | 7 / 7 |

Per object, nominal (inside matched STOP rows / inside visible; first STOP m), control → 1.1.0:

| recording | object | intent | control | 1.1.0 |
|---|---|---|---|---|
| doubleT_obstacle | person_crossing | inside | 61/61; 55.51 | 61/61; 55.51 |
| doubleT_obstacle | object_on_rail | inside | 153/185; 55.99 | 153/185; 55.99 |
| doubleT_obstacle | person_walkway | outside | outside STOP rows 0, episodes 0 | outside STOP rows 0, episodes 0 |
| cloud_with_fake_obj | big_center | inside | 209/213; 98.16 | 209/213; 98.16 |
| cloud_with_fake_obj | small_on_rail | inside | 26/49; 47.96 | 26/49; 47.96 |
| cloud_with_fake_obj | small_center | inside | 32/79; 55.84 | 32/79; 55.84 |
| cloud_with_fake_obj | small_edge_inside | inside | 18/83; 34.97 | 18/83; 34.97 |
| cloud_with_fake_obj | small_outside_near | outside | outside STOP rows 0, episodes 0 | outside STOP rows 0, episodes 0 |
| cloud_with_fake_obj | big_edge_inside | inside | 15/125; 28.21 | 15/125; 28.21 |
| cloud_with_fake_obj | big_outside | outside | outside STOP rows 9, episodes 1 | outside STOP rows 9, episodes 1 |
| cloud_with_fake_obj | big_above | inside | 56/124; 111.42 | 56/124; 111.42 |
| cloud_with_fake_obj | long_low_on_rails | inside | 53/86; 88.97 | 53/86; 88.97 |
| cloud_with_fake_obj | thin_hanging | inside | 15/42; 30.12 | 15/42; 30.12 |

Directional acceptance rows: **260**, failing **0**; status **PASS**.
