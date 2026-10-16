# Execution details, registered before H4 measurement

The protocol at e39a011 remains authoritative. This addendum resolves implementation
details before running the independent probes; it does not replace the registration.

* B = complete `roundT_doubleT`; S = complete `squareT_platform_squareT_switch`.
  Dropout is applied to decoded vehicle-frame returns using a fresh RNG (461023)
  for each recording. Save every mask hash and original cache byte hash.
* Ride pieces are zero-based `numpy.array_split(all naturally ordered files, 8)`
  pieces 1 and 3, as in H3. Use original receive stamps and fresh detectors.
* Observation-only dark band: wrap the shipped `top_is_free` call. Compute the
  candidate's maximum elevation, median top-ring slant range (within 0.06 degrees
  of maximum), and azimuth span. Remove from the observer only returns within
  max(0.5 m, 2% range), above the top by >0.04 and <=0.6 degrees, over the azimuth
  span padded by 0.12 degrees. Remap the unchanged candidate indices into a new
  FrameRays. Candidates, fitted model, intensity, input cloud and tracker are
  otherwise untouched. Record removals, original/masked answer and spare processing.
  This is explicitly an artificial sensitivity experiment. Physical absorbing
  bands use nearest-hit ray extinction, with no farther return replacing a hit.
* Physical scenes use one echo, azimuth -50..50 degrees at the registered phase,
  the production Pandar grid (sensor specification only), floor at rail-head
  height zero. Clustering receives the known physical corridor coordinates and
  shipped envelope/core mask; this isolates clustering + shipped tracking rather
  than claiming end-to-end fitted-axis performance. Run the full distance/lateral/
  width/height/ring/dropout factorial. Add banded ceiling columns at both band
  endpoints for every distance/lateral/width; beam controls at each distance
  (+0.68 m, width 0.46, top 2.72, beam underside 3.05 m), and three-column scenes
  at 37/67/109 m. Snapshot all 20 tracker updates. Identical-frame cluster results
  may be reused via deep copy; frames 9/10 omit object returns (no background fill).
* Surface controls use front faces sampled every 0.045 m across, 0.13 m vertically,
  with side surfaces connecting their sides to the registered smooth surface at
  0.13 m depth increments. These are analytic component inputs, not ray-cast inputs.
  Also feed single-column and two-column faces spanning 0.099/0.100/0.101 degrees
  directly to the shipped part extractor, with one/two echoes. Record actual
  float32 span; do not assume a nominal boundary survives float32 conversion.
* Low-duplicate/state witness: actual shipped duplicate filter, then actual tracker,
  using a newly spared cut part, a geometrically separate low cluster whose boxes
  overlap within the filter margin, and empty corridor-foot samples. It is a
  constructed call-boundary witness; separately check whether the analytic surface
  component yields such a spared cut part. No claim of physical realizability
  follows from the constructed witness alone.
* Azimuth oracle compares exact masks using float32 products, matching the public
  window contract. Include x<=0 and bucket-boundary returns; count all mismatches.

Run one source worker at a time in a <=2 GiB container, numerical threads=1,
native enabled, PYTHONHASHSEED=0. Retained H3 source volumes and original data
are mounted read-only. All generated outputs live in H4's external scratch.
