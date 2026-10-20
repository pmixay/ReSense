# R3 sustained-range follow-up — registered 20 October 2026

Request: investigate the Set F cable sustained median 34.2 ->17.8 m, correct
the cause and integrate the verified result into main.

## Fixed investigation

The historical R3 report already proposes a population-composition explanation.
Do not assume it is true, change detector thresholds to improve an aggregate,
discard newly detected sequences, or overwrite the original metric.

1. Independently recompute held90 from every raw Set F row, sorting visible
   distances and counting exact hits (at least five visible rows, >=90%).
2. Re-run the exact registered Set F protocol on current main: files
   46,68,98,140,168,172; kinds person,box1.0,box0.5,trolley,cable in this order;
   start220 m,110 frames, seed0, lateral -0.6:0.6, legacy placement, bed,
   no supplied speed. All kinds are required to retain the original RNG draws.
3. Compare R3 off (`tracking.cable_confirm_time_s=0`) with the current default
   R3 on. No other parameter changes. Keep source/cache hashes, every raw row
   and immutable execution receipts. Compare frame/placement/visibility identity
   before interpreting any output difference.
4. For every sequence, check exact lost/added hit sets, first detection, held90,
   false detections and visible counts. Report both the original conditional
   median and the baseline-success cohort, including any lost successes.
5. Exercise the analysis with a known lost hit, lost sustained success, changed
   placement and missing sequence. Inspect raw rows at each changed boundary.
6. If the claimed detector regression exists, fix it and run affected tests plus
   gate/X3/Falcon on the detector change. If only changing successful-population
   composition causes the scalar drop, repair reporting/comparison and backlog
   attribution, retaining the scalar and all successes. Verify the original
   acceptance metrics are not weakened. H1, L16/F1a/R3 review issues, independent
   final acceptance and reseal remain separately tracked.

Development data only; no G3, judging, release or new seal.
