# First unchanged-production run

Test-first commit `e623aad` was measured before any tracking patch in an isolated
Linux clone. The required frame-11 STOP assertion failed with both default and
opt-in fresh evidence settings. The independent physical caster also reproduced
exactly STOP frames 5..9 and 12..19; genuine column-to-vault had zero STOP frames.
Native `.so` loaded from the clean clone; Open3D 0.19.0 was available; zero skips.
Full retained run: `red-e623aad/`.

That initial run also exposed seven errors in the new control-test expectations:
the measured-column/spare sequence invokes a second column hold, zone voting can
keep the early advisory below the gauge vote before the explanation gate acts,
three advisory hits age spares out of a three-hit window, and doubt spends its
budget on the explained-blocked advisory as well. The follow-up test-only commit
isolates the explanation control with column hold disabled, inspects blocking only
when the rule vote is gauge, uses ordinary evidence for the fresh-gate control,
and matches the existing doubt timing. The separate column-hold test still uses
published defaults. No production change is made to satisfy these control errors.

The corrected test-only commit `abd09df` yields **2 failed, 248 passed, zero skips**:
only the two frame-11 regressions fail, with fresh evidence disabled/enabled.
All controls pass before the production patch. `red-abd09df/` retains the exact
source identity, outputs and paired physical histories. Physical STOP frames are
again 5..9 and 12..19 for case 44 and none for the genuine column-to-vault.
