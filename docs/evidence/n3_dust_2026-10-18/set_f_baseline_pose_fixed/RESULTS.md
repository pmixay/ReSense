# Set F dust baseline: complete fixed-placement battery

All 30 object/ride sequences completed at clean, low, medium and high density.
Source, raw-output and frozen-placement hashes were checked before this report.
The original maximum is 110 frames; each sequence stops when its target passes 8 m.
Every density uses the identical frozen sequence and retains clean physical truth
when attenuation removes its returns. These are simulated stresses, not measured dust physics.

| Level | Frames | Matched STOP rows | Lost clean STOP rows | Unmatched STOP frames / episodes | GO | Degraded |
|---|---:|---:|---:|---:|---:|---:|
| clean | 3060 | 1064 | 0 | 23 / 11 | 1501 | 0 |
| low | 3060 | 1027 | 61 | 18 / 13 | 1533 | 0 |
| medium | 3060 | 752 | 392 | 1480 / 275 | 385 | 0 |
| high | 3060 | 14 | 1050 | 183 / 58 | 2311 | 0 |

Episodes are summed within independent sequences, never joined across runs.
Unmatched detections are reported under the original fixed matching tolerance;
Serialized detections have 1 cm precision; independent matching uses explicit
rounding bounds and retains any boundary ambiguity in aggregate.json.
the real backgrounds are not exhaustively annotated. Zero matches at every
density remain visible below rather than being silently excluded.

| Sequence | Frames | First STOP m: clean / low / medium / high | Lost clean rows: low / medium / high |
|---|---:|---|---|
| 46_person | 102 | 169.22 / 158.65 / 158.65 / 70.78 | 7 / 27 / 53 |
| 46_box1.0 | 102 | 146.02 / 108.04 / 108.04 / — | 2 / 17 / 37 |
| 46_box0.5 | 102 | 76.94 / — / — / — | 3 / 3 / 3 |
| 46_trolley | 102 | 156.60 / 108.04 / 105.95 / — | 11 / 27 / 47 |
| 46_cable | 102 | 56.42 / 56.42 / 64.62 / — | 0 / 8 / 8 |
| 68_person | 106 | 144.10 / 117.98 / 119.88 / 69.58 | 2 / 19 / 49 |
| 68_box1.0 | 106 | 109.93 / 112.02 / 107.97 / — | 0 / 15 / 51 |
| 68_box0.5 | 106 | — / — / 23.06 / — | 0 / 0 / 0 |
| 68_trolley | 106 | 112.02 / 148.10 / 148.10 / — | 0 / 13 / 52 |
| 68_cable | 106 | 107.97 / 105.99 / 130.08 / — | 1 / 5 / 23 |
| 98_person | 106 | 152.04 / 152.04 / 152.04 / — | 0 / 23 / 72 |
| 98_box1.0 | 106 | 108.00 / 108.00 / 108.00 / — | 0 / 18 / 50 |
| 98_box0.5 | 106 | — / — / — / — | 0 / 0 / 0 |
| 98_trolley | 106 | 103.88 / 103.88 / 97.72 / — | 0 / 13 / 48 |
| 98_cable | 106 | 103.88 / 108.00 / 134.08 / 75.50 | 0 / 13 / 25 |
| 140_person | 110 | 149.57 / 140.16 / 140.16 / — | 6 / 21 / 72 |
| 140_box1.0 | 110 | 149.57 / 149.57 / 145.77 / — | 1 / 19 / 57 |
| 140_box0.5 | 110 | — / — / — / — | 0 / 0 / 0 |
| 140_trolley | 110 | 193.99 / 193.99 / 151.32 / — | 1 / 21 / 54 |
| 140_cable | 110 | 93.83 / 93.83 / 93.83 / — | 3 / 7 / 21 |
| 168_person | 78 | 166.28 / 166.28 / 166.28 / 10.68 | 0 / 5 / 38 |
| 168_box1.0 | 78 | 131.78 / 129.87 / 120.40 / — | 2 / 7 / 26 |
| 168_box0.5 | 78 | — / — / 12.61 / — | 0 / 0 / 0 |
| 168_trolley | 78 | 154.77 / 154.77 / 110.64 / — | 0 / 24 / 40 |
| 168_cable | 78 | 12.61 / 104.94 / 143.24 / — | 0 / 0 / 3 |
| 172_person | 110 | 149.91 / 142.40 / 140.43 / — | 5 / 24 / 72 |
| 172_box1.0 | 110 | 116.10 / 105.17 / 105.17 / — | 6 / 18 / 55 |
| 172_box0.5 | 110 | 51.87 / 51.87 / 38.86 / — | 0 / 8 / 20 |
| 172_trolley | 110 | 148.06 / 148.06 / 105.17 / — | 7 / 26 / 58 |
| 172_cable | 110 | 112.52 / 105.17 / 110.70 / 71.94 | 4 / 11 / 16 |

See [aggregate.json](aggregate.json) for every lost row and first-range ratio,
[summary.json](summary.json) for per-level results/source hashes, and
[placement_manifest.json](placement_manifest.json) plus `placement_bank/` for the frozen objects.
No dust-suppression or health-only runtime candidate is activated by this battery.
Measurements shared the single-CPU host; they do not establish isolated throughput.
