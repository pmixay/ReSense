# M2 production validation

The production patch translates the preregistered thin-evidence observer without changing
detector thresholds or tracking. The candidate is in `work/monitoring-quality-20260926`;
integration remains conditional on the remaining runtime/raw/stress checks.

- **Exact observer parity:** all 15 captures / 15,269 frames equal the registered observer
  output, excluding only informational timing. No range estimate increases.
- **Full regression:** all 199 comparison rows retained; all 146 enforced metrics unchanged,
  no missing values, regressions or waivers. The 16 changed rows are informational timing.
- **All 72 original placements:** every case and per-frame row is exactly equal to the original
  study (45 matched cases, 544/2,458 visible frames, zero matched controls).
- **Monitoring costs:** every empty recording and the full ride pass the registered budgets.
  Target diagnostic range overclaims fall 54→44; GO overclaims fall 46→36. This remains a partial
  improvement and does not establish free track or meet the central zero-overclaim objective.
- **Production-path test:** supported thin evidence caps range and raises uncertainty without
  starting a STOP; evidence disappearing on the next frame removes the cap; the existing
  `health.clear_cap=false` switch disables it.

The gate was measured with committed source `a9be98b`; production behavior was introduced in
`482caab`. `parity.json` records every source hash and paired capture. `gate_frames/` retains
all measured frame outputs, and `novel_result.json.gz` retains every placement case.

Set O labels inherit a prior fitted rail model. No new real-positive recording is available.
M2 changes monitoring uncertainty; it does not improve detection recall or false STOP counts.
Release and final quality freeze remain on hold.
