# P3 handoff: separate curve bias from standing-axis noise

The [offline crosswalk](README.md) is complete. **K1 and K2 remain open**;
it authorizes no detector change or default activation. The existing ownership
map assigns P3 detector/native/config implementation, P4 independent measurement
and safety review, and P1 integration, full acceptance and resealing. This is a
prepared handoff, not a claim that another member has accepted new work.

## Issue provenance and separation

P4's L10 curve limitation concerns primarily **K2**: systematic path curvature
error and double-track ambiguity. In B, archived raw-wall/ICP curvature is
approximately −0.0023 to −0.0027 /m, while the detector is approximately −0.0006
to −0.0011 /m. C's previous wall-reference study locates 1.0–2.4 m error at
100 m in frames 57–117. The smooth inner wall carries 3–10× the fit weight but
is visible only to 56–96 m; a single quadratic tied to the near rail tangent
also limits a growing transition curve. Measured EMA lag was only about 1.5
frames and the curvature rate limit was not binding there. Smoothing alone
does not address that bias.

**K1** concerns noise and STOP flicker at standstill. On `squareT_platform`
frames 360–620, the prior placed-object experiment measured axis SD 0.30 m at
100 m and 0.67 m at 150 m, versus object lateral variation 0.095 m; the empty
axis SD at 100 m was 0.094 m. Object occlusion of wall observations is a
hypothesis, not an established cause. X1 also identified tracker holds and
far-evidence admission constraints. A display-only EMA cannot demonstrate
improved detector STOP retention, and a moving-curve ICP result cannot replace
K1's standing-object tests.

The cards and exact historical acceptance are in
[BACKLOG K1](../../../BACKLOG.md#k1--standing-train-far-axis-jitter--stop-flicker-at-100150-m-perturbation-sensitive-platform-false-stops)
and [BACKLOG K2](../../../BACKLOG.md#k2--curve-and-double-track-axis--read-the-round-3-evidence-first).
This handoff reads the evidence at `cf188486f5c2339cd74adcb52ecdd21a59f8fad0`
and P4 B6 at `1b880168ce2dbeec2071838892ac05eed5a9166a`.

## Existing mitigations and rejected changes

| Work | What the evidence supports | What must not be claimed |
|---|---|---|
| Shipped `axis_wall_drift=0.8` honest-range cap | Restricts health monitored/clear range when wall drift is observed; C's B6 >1.05 m fraction falls 12.54%→2.17% | It does not move the fitted axis or repair the detection corridor. B remains 41.22%→40.13%. |
| N1 bounded, smoothed display | Its original visible-pair 3D movement thresholds pass; the visible extent is explicitly limited | It is not K1/K2 acceptance. B's same-visible-point path error and 40 m ICP step worsen slightly; far-pair coverage is small. |
| Rejected `r3/axis-B-trial` wall-span weighting | Span-ratio⁴ weighting with gaps up to 16 m improved C's 100 m median wall error 1.39→0.42–0.56 m and wall-referenced person first STOP 71→96–111 m | All three variants failed full controls: ride events 27→33/36/34 plus other empty alarms. Do not repeat the local gain as an accepted fix. |
| Rejected cap of `axis_valid` at wall drift | More conservative corridor admission | C person STOP frames fell 55→43 and first STOP 82.8→65.1 m; this was not selected. |
| N6 platform rail-support candidate | Separate measured person gain with unresolved support/occlusion dependence | Default remains off; it does not establish a general curve fix or justify unsupported trust extension. |

The detailed prior trial and range-cap record is in
[CHANGELOG](../../../../CHANGELOG.md#fixed--the-monitored-range-stops-where-the-axis-leaves-the-track-at-a-curve-entry-trackaxis_wall_drift-1510)
and the archived
[round-3 harness catalog](../../silent_misses_2026-10-14/harness/README.md).
`r3_axis/obs_C.json.gz`, `B_true_axis.json.gz`, `cf*.py.txt`, `cflib.py.txt` and
`axhooks.py.txt` preserve the observations and prior offline studies.

## Concrete next step and acceptance boundary

P1/P4 can now use the frozen crosswalk and pair masks to explain L10 without a
new run or a misleading comparison of p90 values. The next **P3** step can also
start offline: inventory the existing C wall observations and B reference,
then preregister one supported geometry hypothesis and compare residuals by
distance on those fixed observations. Candidate families already listed in K2
are outer-wall use only where independently supported, a piecewise transition
model, or double-track side selection anchored to the observed near rails.
Preserve conflicting observations and report support gaps. Do not merely extend
`axis_valid`, trim conflicting evidence, weaken tracker holds, or redefine
object placement from the candidate axis to manufacture range gains.

Use one P3 owner for `track.py`/tracker/config changes to avoid overlapping K1,
K2 and return-mode work. Register the measured hypothesis and exact source
before any candidate run; integrate behind a default-off option. Freeze the
object placements/reference paths independently of the candidate. Separate
geometry error, detector admission, tracker confirmation, monitored range and
display availability in the resulting ledger. P1 should combine accepted
changes only after their individual controls and the final combined gate pass.

The existing numerical requirements remain unchanged:

| Card | Positive and geometry requirements | Negative/control requirements |
|---|---|---|
| K1 | Standing person ≥200/260 STOP at 100 m and ≥150/259 at 150 m; 0.5 m cube ≥150/260 at 100 m; preserve ≥255 at 60 m; a newly appearing 100 m object STOPs within 0.5 s | `squareT_platform` ≤1 false-STOP episode; every squareT X3 variant ≤3 and roundT_squareT zero; real `doubleT_obstacle` 193 STOP; full gate exit 0 and safety review |
| K2 | C wall-vs-axis error ≤0.5 m at 80–120 m; C person first STOP ≥110 m and held ≥100 m; B person first ≥90 m and 60–100 m STOP ≥80%; preserve A person 218/222 m first/held | Four named ride curve-edge episodes reduce to ≤1; crossover posts frames 4720–4729 never STOP; full gate exit 0, including ride ≤27 events/30 episodes, and safety review |

K2's prescribed C person is `--obj 0.5,0.5,1.75 --start 0 --d0 230` on
`roundT_pressureGate_roundT`; B uses `--start 50` on `roundT_doubleT`.
The four ride onsets are 3753, 6867, 7859 and 7868. The crosswalk's ICP
trajectory proxy does not substitute for the wall-reference ≤0.5 m criterion,
object STOP tests, false-alarm controls, or safety review. Further runtime work
must bind the actual selected source and retain every lost STOP/range and new
false episode explicitly; the present artifact closes only the evidence
comparison and handoff.
