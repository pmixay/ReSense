# P3 prospective numeric-invariance amendment

Revision3 fixes the requested pure roll cases 4/5: full Falcon has exactly the
same 1,387 STOP rows as the correct explicitly oriented control, with none
added or lost. It is still NOT accepted: cyclic axis case12 recovers/replays
but loses seven control STOP rows and adds 35. Those raw rows/source remain
under `run3/`; interrupted current-source gate/node work is not acceptance.

The next hypothesis is float32 coordinate-order invariance. Composing an axis
permutation with continuous tilt changes the dot-product accumulation order.
For the new directional-history recovery only, first apply the known discrete
signed permutation exactly, then the continuous tilt in canonical vehicle XYZ
order. Existing mappings keep their original application path. The public R
still represents the same complete physical transform.

Before replays: add all-24-rotation geometry tests with nonzero tilt; they must
fail on the old composed apply and pass on the candidate. Re-run complete
Falcon, all B4 controls and combined gate on the exact candidate. Preserve
every lost/added frame, including the previously failing native-axis case12.
