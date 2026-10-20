# Revision 3: retain a missing-floor cap without a new time-based expiry

Registered after the r2 Falcon replay and **before** the r3 edit/measurement.
R2 source: `180c16c6` (detector edit `7c0dfe56`). The original r1/r2 results
remain recorded; this revision does not turn their failures into passes.

The full Falcon replay exposes a cost of the r1 policy: 42 changed rows versus
the original v5c-15, seven additional lost original person STOP frames
4366–4372. The 20 m-per-period expiry is an author-added policy, not a necessary
part of preserving the cap. With a standing train, missing floor samples do
not imply 20 m of travel every 0.1 s. The original estimator holds its floor
and axis on this path; expiring only the joint output removes near-object
observations from an otherwise held corridor.

R3 policy:

- A missing fit retains at most the **last capped output** ranges, dual marker
  and wall-drift restriction. It cannot restore the uncapped base or add another
  dual extension. Repeated missing-floor frames cannot enlarge these limits.
- When the bed is fitted but walls are unavailable, retain the previous cap
  and intersect it with the ordinary base estimator's shrinking range. The
  repair does not introduce a second, faster decay or change that base state.
- Fresh usable boundaries replace the old restriction. Cold starts cannot
  invent joint support. The cap also survives a switch back to the base shape
  while boundary observations are absent, including empty boundary arrays.
- K1's r2 elapsed-period correction remains. Both switches remain off by default.

Tests: revise missing-floor tests to assert a finite hold, repeated loss and
recovery; add the empty-boundary/base-shape transition regression before the
edit. Off and cap-disabled controls remain mandatory. Repeat the complete
4,443-frame Falcon pair against the unchanged original source, report original
person retention and every delta against r2. Required outcome for this policy
repair: no new person loss versus original v5c-15; no restriction release on
missing observations. Existing small_center, tunnels and Falcon v5c losses
remain acceptance failures until independently repaired and measured.
