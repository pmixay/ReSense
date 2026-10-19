# Fixed supplementary preservation checks

Registered after nominal R3-v2 screening, before these new runs; no candidate
tuning against their results is permitted without recording another variant.

* E6 standing cable on the original frozen placement: nominal, pitch+2/-2,
  roll+2, dropout30% seeds1/2/3/7, and exact-XYZ dedup. Apply transforms after
  insertion to the entire sensor cloud, as the judge probe does. The unmodified
  judge scoring/placement and pre-perturbation visibility denominators remain.
  Require no lost baseline matched STOP row; report every new unmatched detection.
  The ordinary 40-case X3 already supplies5 Hz and hanging-cable perturbations.
* Re-run A-axis (0.3x0.3x2.8) and C-person (0.5x0.5x1.75), same archived X1 ICP,
  current-main object-free placements and both sources. Use the local raw C bag
  to create its missing node-decoded cache in scratch; no download.
* Actual full4,443-frame Falcon, normal input on both sources; preserve old
  detection/STOP rows and record additions. This checks the inherited L16/S3 base.
* Independently validate decoded XYZ/intensity/ring against direct NumPy views of
  original SQLite/CDR for distributed samples in all four X3 bags. Historical
  1.1.0 NPZ-container hashes differ on this VM; numerical comparison to its40
  hash-verified raw reports is supplementary, not strict identical-input PASS.

Full gate has passed, but one *informational* sustained median for Set F cable
decreases34.2->17.8 m despite zero lost matched rows and nine additions. Check the
per-sequence sustained values / changing population before attributing this
aggregate shift. Do not silently drop the worse informational metric.
