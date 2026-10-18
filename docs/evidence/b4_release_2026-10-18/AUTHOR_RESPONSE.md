# Response to independent P4 review

Prospective protocol committed at `0a68b11` before this revision. Historical
uncommitted-author evidence and the initial blocking P4 report are preserved.

* **B1:** replay the actual voting samples into the spaced observation stream,
  selecting every sample eligible under `obs_spacing` and preserving elapsed
  frame-period timestamps. Evaluate due provisional/final calibration on the
  adoption frame too, retaining the axis-permutation reseed flag. This restores
  `frames=5, obs_spacing=1` final calibration from frame 5 to frame 4 and the
  actual matched person STOP from frame 9 to frame 8. Added cadence controls
  cover spacing 1/3/10, periods 1/2/5, time-cadence on/off.
* **N2:** require three resolved cone-plane offsets, separated by >=0.005 in
  unit-ray coordinates, rather than only a three-ID fit plus total span. Added
  rejection control for three IDs on only two planes.
* **N1/N3/N4:** retain explicit limits: late usable rings cannot invalidate an
  already confirmed mapping; scan axis is not gravity; hardware channel/source
  provenance is assumed; jury associations are not separate-object proof.
  Physical horizontal mounts and ring-free Falcon remain outside this B4 claim.

Initial revision check: 57 directed tests passed; independent real-data
`directed_checks.py --assert-no-loss` passed, both short-window cases first STOP
on frame 8 with no lost person frame. Full acceptance below must be on the
committed revision, not inferred from those preliminary checks.
