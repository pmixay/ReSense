# Directed replay plan / amendment after forcing screen

Saved after exploratory forcing and before final directed capture. This is a
conditional synthetic failure search, not a blinded estimate of incidence.

The 72 first forcing trials selected the host, not distractors. The second
screen (120 trials, including deliberately absent-host estimator controls) found
actual non-host fits when host rise is 0.20 m and distractor rise is 0.30 m.
The third screen (72 trials) did not find a wrong fit for the standard 0.35 m
host. These are new trials, not the historical 72 ambiguous-pair scenes.

**Oracle clarification:** varying host rise changes its head Z. The analytic
envelope uses `bed + host_height` (thus -1.98 m for 0.20 m host rise), never
assumes -1.83 for that scene. The target base stays at -1.83; it stands 0.15 m
above this host head and still supplies observed body collision points. Default
0.35 m-host controls use -1.83. Both 0.20/0.30 m rises are physical box-ridge
surrogates, not exact rail cross-sections; the semantic host is declared input.

Final full-default-detector cases: correct inside/outside; +/-0.4/0.6 m
distractors, both outside (1.29 or 1.50 m) and opposite-side inside (-/+0.68 m)
targets, at 17/37/67 m as specified in `h1_run.py`. All selected fits, not only
successful wrong fits, are captured. In particular 1.50 m lateral gives a
0.22 m geometric gap from the host envelope, a stronger outside control than
the 0.01 m gap of 1.29 m. No requirement to manufacture a failure at every offset.

No-rail cold starts use real rail-free casts at 17/67 m with bed -2.18 and a
separate -1.83 floor. Loss runs contain 14 rail-positive warmup scans followed
by 14 scans without rails, with/without target. Physical shadow box at 7..9 m
tests actual floor-held state, with an independent shadow-removed continuation
control. All scans, including the warmup, are saved.

Component-only: standard host with extra outer rail, supplied center +/-1.59 m;
test actual estimator selection and core without claiming full detector. A
supplied `floor_held=True` model is a component guard test only.

Acceptance means **evidence validity**, not universal detection PASS: byte-exact
plain/traced non-timing results and tracker state; independent raw ray/geometry
and selected-fit verification; every core invocation rechecked with scalar
erosion; actual positive correct-pair/core/STOP controls. Any unsatisfied item
is recorded as failed or UNVERIFIED. Do not silently remove failed trials.
