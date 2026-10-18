# N6 revision 3: preserve the low-bed evidence boundary

Revision 2 at `5b305a3` improved the platform person from 44.01 m to 51.12 m,
retaining all 147 baseline person STOP rows and adding 11. It failed the first
empty-recording control: `doubleT_platform` acquired six low-object STOP frames
(30–35; one episode) against zero in the baseline. The measured rail extension
was active at frames 23–28 and admitted additional low-bed candidates that
confirmed later. Axis shape remained identical.

Revision 3 keeps the raw paired-rail rule unchanged and gives the low-bed stage
the **pre-extension** trusted range. Lateral rail support alone does not justify
extending the bed-anomaly model. All low, straddle and central-near candidate
admission takes place inside that stage; its input range and learned geometry
remain the baseline values. Ordinary above-rail corridor clustering can use the
observed lateral support. No obstacle points are removed by a new intensity or
shape filter.

This hypothesis is registered before the revision-3 replay. Acceptance remains
the parent [protocol](../lidar_adaptation_2026-10-18/PROTOCOL.md): improve the
person's first STOP above 44.01 m, preserve every baseline person STOP, add no
unmatched/outside STOP on the three annotated recordings and no STOP on the
exact source interval or five empty recordings. Unknown gauge cases remain
unknown, with bounds reported. The 60 m target is desirable and has not been met.

The focused test executes the real detector process and captures the low-stage
range argument, including a zero original range. The geometric tests retain
isolated-edge, wrong pairing, duplicate-return, missing-ring and unsupported-gap
controls. Full gate and independent frame-level review are still required before
changing the default or sealing this candidate.

Replay source will be exported from the measured commit for all control runs,
so concurrent N2/N3 integration edits cannot contaminate N6 comparisons.
