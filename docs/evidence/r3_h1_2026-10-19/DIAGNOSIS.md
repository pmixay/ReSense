# Diagnosis and registered candidate hypotheses (before detector edits)

## R3

Current E6 exactly reproduces the archived control: first 59.78 m, held 43.37 m,
29/59 visible matched STOPs. Every range JSON field equals hooks-off. On its 30
missed visible rows the recorded first causes are confirm_hits 22, confirm_time 6,
hit_fraction 1, beyond_axis 1; independently re-evaluated 8 full-state samples,
all confirmed. Example: k278/279 (86.25/84.81 m), track65, hits3/4, confidence1,
hit_fraction1, span0.299978/0.399977 <0.5 s. No doubt/association veto is responsible
for those rows. Visibility gaps exceed max_misses: k260/261 -> k267 -> k276,
and k279 -> k284. The point bar and the 60 m hanging-search limit are not the
dominant observed blocker on the standing target.

Set O: the hanging search emits correct groups at k777/778 (49.83/48.19 m)
then a long visibility break; it emits k785..789 (36.74..30.12 m) next.
The first series has only two hits, so expires before 0.5 s / three hits.
Direct inspection of full-stage points confirms footprints <=0.024 m and
vertical spans0.444/0.566 m on the first series. Earlier groups k775/776 lack
the required inside/above-top combination. Preserve those evidence bars.

The old X1 verifier rejects Set O because trace overhead changes latency-only
health messages/diagnostic level. All 791 rows agree after the pre-existing
L16/S3 normalization: discard decode/detect/total timing, remove only messages
starting `latency p95`, use the independently serialized `dlevel` for diagnostic
`level`. No obstacle, decision, detection, warning, geometry or decision-health
field changes. Preserve this failed raw equality result. Before relying on new
attribution, additionally replay a fixed latency input for both modes and demand
strict equality except timing. This is an observation adapter, never detector code.

**Hypothesis R3-v1:** a small, *consecutive current-frame* run of well-resolved
vertical evidence can confirm sooner than generic clutter. Tall thin bodies:
footprint <=0.15 m in X and Y, height >=1.5 m, >=8 strict voxels, clean gauge,
3 hits and >=0.3 s. Hanging groups: same narrow footprint, vertical span>=0.25 m,
>=2 voxels including>=1 strict voxel, clean hanging kind, 2 hits and >=0.2 s.
Retain generic confidence, hit fraction, zone, column, approach and doubt gates.
No accumulation, invented hit, prolonged survival or default free-top. Reset the
special run on a miss, other geometry or provenance. Ordinary confirmation remains
available, so it cannot be delayed by an interrupted special run. Evaluate R3-v1
against the fixed PROTOCOL acceptance; if it fails, retain it as rejected.

## H1

Independent archived physical slab caster reproduces 84 object returns; 80 are
strict-gauge voxels on20 rings. Their observed height is0.162..2.940 m, footprint
X=0, Y=0.350 m, lateral0.684; four more raw returns extend to3.062 m above the
rail head. The physical box is3.22 m high. The current column rule demotes it
solely by height/width, even though *all80 voxels are in the collision envelope*.
Column history then forbids STOP; no amount of confirmation fixes that decision.

The old free-top question is unsound for this purpose: absence of returns above
a cut can be absorption, and positive above-cut continuation is not proof of
safety (a tall load / pole in the envelope can continue above it).

**New approach proposal H1-core:** distinguish positive collision evidence from
infrastructure identity. A vertically resolved, short-depth body wholly inside
the strict collision envelope should not become safe merely because it is tall.
Use an independently supported rail/axis uncertainty tube, require the *entire*
observed footprint to remain inside it under the uncertainty (not just centroid
or majority count), and keep edge/merged/unsupported cases advisory. Treat dark
continuation as unknown, not free. Do not call `top_is_free` or manufacture
provisional explanations. Track ordinary positive collision hits directly so
returning hits need no special unspare discharge.

First evaluate a read-only geometric prototype on physical case45, opaque/dark
continuations, mirrored/lateral boundaries, and all candidate snapshots from the
full empty-ride corpus. In-envelope opaque tall objects are positive collision
controls; genuine outside-edge infrastructure is negative. A physical column
truly occupying the train's envelope is not a valid negative. Fitted-axis-only
tests cannot establish which is which in the real ride: report ambiguous cases.
Do not enable H1 by default without independent axis support, whole-ride dark
checks and P4 review. H1 remains open if this evidence is insufficient.
