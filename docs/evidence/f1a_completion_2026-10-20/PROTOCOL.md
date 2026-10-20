# F1a completion — registered author protocol, 20 October 2026

User requested completing F1a, merging into main and updating the backlog.
Starting source: main `f56ad5e`. Work is isolated in `fix/f1a-completion`;
the separate reference worktree is pinned to that exact commit. P3 author
development and P4-style measurement are separate phases; no G3 data is used.

## Required acceptance, before detector edits

* Preserve both B1 repairs: full current-frame footprint top, and independent
  rail support excluding all low footprints, including weak/advisory ones.
  Retain every fragmented-object control on either/both rails, cant, common
  height error, missing support and the physical raised-rail box/approach.
* Preserve the organizer 30 x 30 x 10 cm rail-head box and thin/sparse upper
  body evidence. Do not require multiple upper returns: a single genuine
  upper return must still prevent suppression without independent evidence
  of rail continuation.
* Recover the original F1a false-alarm benefit: compare chunked and continuous
  ride with both current main and the pre-B1 `8c2bf51` recorded reference.
  Target at most the old 18 events /24 episodes on the chunked ride, without
  losing or delaying labelled obstacles on any recording. Explicitly retain
  the distinction between chunked and continuous replay.
* Strict complete gate (no `--allow`), Set F, unchanged standard X3 workers,
  whole Falcon, affected tests and full pytest. Account for every changed
  decision and investigate any detection loss, not only aggregate metrics.
* Instrumentation must equal plain replay outside timing-driven fields.
  Inspect raw point examples; independently derive each rejection from raw
  support and record the actual production branch. Include positive controls
  for zero differences and zero lost detections.
* Commit measured detector source before final acceptance runs. Retain exact
  commands, source hashes, raw outputs and failed/intermediate attempts. A
  seal is source integrity, not independent review or release acceptance.

## Candidate mechanism registered before its implementation

P4 traced rail fragments whose low-stage top passes the old rejection but
whose repaired top includes rail-head returns above the stage's cap. The
median rail reference often describes the rail web instead of its head.

Evaluate a conservative additional **rail-surface continuation** condition:
only old-rule-eligible, narrow low fragments reaching a rail line qualify.
Use full footprint top and independent returns outside *all* low footprints.
Require rail-band support both before and after the cluster, outside the
existing 0.3 m guard and inside `local_rail_window`. Each side needs occupied
along-track bins; use existing bin/support settings. Compare the candidate
with an interpolated upper rail surface from those independent supports,
using the existing rail-geometry margin (`rail_start_margin`, 0.05 m), not a
newly tuned tolerance. No continuation support, no additional rejection.
The original minimum-of-two median-reference rule remains unchanged.

This is not a blanket top cap, an upper-return-count threshold, a cross-rail
substitution, a tracking-speed veto or a recording/frame-specific rule.
Both-side support and exclusion are mandatory, including when the unsafe
`local_rail_exclude_low=false` ablation is explicitly selected: the new path
must not turn that ablation into a second self-support mechanism.

First inspect captured raw states and directed counterexamples; record any
amendment here before modifying the production mechanism or measuring it.

### Raw-state clarification, before production edits

The historical archive contains all 98 flipped-cluster snapshots, not all
206 old-rule rejections; the first inspection requested a missing non-flip
snapshot and stopped. Restricting the diagnostic to the documented 98 flips
corrected that input assumption. A fixed expected-rail band recovers 79/98
but misses shifted rail-head returns. The continuation must follow the
candidate's **own observed narrow lateral interval**, not assume that a
model-axis +/-0.10 m band contains the actual rail head. Eligibility still
requires that interval to reach an expected rail line; no widened footprint
or cross-rail substitution is allowed. This uses the same-band geometry of
the existing `rail_band_range` / `mark_rail_line` rules.

Initial red-test fixtures had two errors: a 0.40 m upper return exceeded the
existing `foot_max_top` cap, and the missing-support fixture removed the
target's upper return too. Corrected to <=0.34 m and removal outside the
target guard before production edits; the original failing XML is retained.

### Two-sided support strengthening after targeted check A

The first candidate passed 154 targeted checks but failed the missing-before
head control: interpolation between a low web on one side and a high head on
the other could manufacture sufficient height at the target. Strengthen the
condition before further measurement: **both side heights separately** must
support the footprint top within the existing 0.05 m margin. Use the lower
side height, never an interpolated height above it. This deliberately fails
open on a steep grade or one-sided head observations. Keep targeted-A XML.

### Measured variant B and the raw-state reading of the rail head

Variant B (both side heights, lower one) passed the strict gate: ride alarm
events 23 -> 20, STOP episodes 26 -> 25, alarm frames 111 -> 108 against
current main; every other recording and every set O object identical; the
gate passed with no waiver. It recovers 77 of the 98 archived flips. The
residual cost against the pre-repair rule is +2 events and +1 episode.

The raw frames explain what the rule compares. On the ride **both** rails
read bimodally and synchronously: the lower mode (0.05-0.11 m) is the rail
web, the upper mode (0.18-0.23 m) is the head's top surface. The model's
rail-head plane therefore sits about 0.1 m below the real head top on this
stretch. The F1a reference is the **median** of the band, so it reads the web;
the B1 repair's uncapped top reads the head's top. The comparison was
apples to oranges, and the repaired rule reported the head's own top as an
object's body. The variant-B surface is likewise a web reading.

The reference must read the **same feature** the top reads. Amendment before
the second production edit: the independent surface is the head's **top
surface** in the candidate's own lateral band - the highest low-free return
in the band, not a median - with these conditions, all parameter-free:

* the candidate is narrow and its lateral interval reaches an expected rail
  line (the existing ``rail_start_max_width`` / ``rail_start_lateral``
  geometry of ``mark_rail_line``);
* the band's height window is the same one the top uses (``foot_max_top``),
  so both sides of the comparison describe the same surface;
* both along-track sides must carry at least one low-free band return, so a
  one-off structure cannot define the surface;
* the surface must be seen by **at least two distinct returns** within
  ``rail_start_margin`` of it (the cloud holds every return twice, so the
  support is counted on distinct ``(x, dy)``); a single stray return fails
  open;
* the candidate's uncapped top must not rise above that surface by more than
  ``rail_start_margin`` (the existing 0.05 m, half the organizers' 0.10 m
  object).

The eligibility gate is unchanged: only a cluster the **pre-repair** F1a rule
rejected (capped top below the original median reference) can be rejected
this way. The new rejection set is therefore a subset of the pre-repair
rule's, which on the recordings contained no real object (T4's independent
visual exposure). Keep the variant-B XML and gate report.
