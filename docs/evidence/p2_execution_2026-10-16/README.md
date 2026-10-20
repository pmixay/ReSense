# Role 2 execution receipt — 16 October 2026

Branch: `role-2`. Starting SHA: `cfae4ba9334df6912c9e2c336dea4eb1c1865935`.
Implementation receipt; **not overall P2 completion or a new system score**.
See [owner handoffs](HANDOFFS.md) for inputs, provenance and dependencies.

## Latest handoff and draft

P4 `6d6aaca` received: [independent intake](P4_INTAKE.md) confirms the register,
numeric export and durable archive. Export format accepted by P2. The new
18-slide draft deck and charts (folder `docs/presentation/draft_2026-10-16/`, removed 19.10; git history keeps it)
use those verified sources; source-backed X1/range, X3 and attribution charts,
corrected object captions, PPTX and rendered PDF are prepared for owner review.
Full browser acceptance passed **47/47** on a frozen frontend build.
The package table below records the earlier implementation checkpoint; this
update closes its P4 export/raw delivery and draft-chart preparation items.
Release J1, final-media reconciliation and P1 approval remain pending.

## Scope and acceptance

| Plan package | Implemented / prepared | Remaining acceptance |
|---|---|---|
| P2-01 | fetched participant refs; release/checkout distinction; measured overview 180 s; docs index/demo ownership; additive output docs; P4 source and marker handoffs | P1 shared-doc review; P4 DATASET correction and numeric export agreement |
| P2-02 | static dashboard and React Live/Player/RunDetail reason presentation; typed optional fields; invalid-data handling; published JSONL decisions preserved; shared v1 metadata on new jobs; ROS freshness and retained STOP; marker reasons | P1 review; real selected-image ROS/RViz/Foxglove and screen-size visual acceptance |
| P2-03 | historical artifact checks use explicit declared gate; separate node-source parity checker and deterministic full-table draft renderer; common resolved JSON for future media | P4 export agreement/J1/X3/raw archive, final geometry charts/cards, final PPTX/PDF visual review and approval |
| P2-04 | release identity/offline/warm-up/demo labels and actual rehearsal requirements added to runbook | permitted release, new matched fallback/video, two devices, two actual timed rehearsals |
| P2-05 | physical-core topology checked; exact-image/kit/matrix handoff prepared | ≥8 physical-core host/operator, final release, agreed protocol and all 12 matrix runs |
| P2-06 | acceptance and owner handoff documented | final release/results/media reconciliation, deployed identity/public links, P1/P4 sign-off |
| P2-07 | scheduled after 23 October | D2/X2 owner-coordinated archival and episode visuals |

## Behavioral coverage

* Distinct known CAUTION reasons translated into Russian; unknown codes stay text;
  missing legacy metadata explicitly unavailable; explanations disappear off CAUTION.
* Static JSONL/label boundary rejects malformed optional fields. Dashboard keeps
  existing health/freshness guards and STOP priority; explicit stored decisions
  are not overridden merely by an aggregate warning flag.
* React HTTP and live status boundaries validate optional metadata and flags.
  ROS requires current node clocks/ages, not just recent receipt; malformed messages
  cannot refresh a green state. Last STOP survives a stale/watchdog fault until a
  current valid result releases it. Source-generation callbacks are invalidated on failure.
* Backend import retains historical decisions/reasons. New computations use the
  shared Python v1 oracle. Integration test follows worker → storage → HTTP → simulated WS.
* GO wording and monitored-range labels no longer promise guaranteed free path.
  Simulation remains labelled replay; no simulation timing is credited to the detector.
* Node marker text shows both object and health reasons from the shared policy.
  Detector configuration/seal and runtime policy remain selected v1.

## Verification environment

Host: Linux, Node 22.22.1, npm 9.2.0. Browser/video initial diagnostics also used
`/tmp/opencode/resense-p2-venv` (Python 3.14.4, Playwright 1.64.0).
Full Python/browser checks use disposable container `resense-role2-checks`, based on
local `resense:ci-local` with Python 3.10.12, NumPy 1.26.4, Open3D 0.19.0.
Current root package/native kernels built in `/work`; source mounted read-only at
`/source`; backend tests import current `/source/webapp/backend`. `/work/configs`
is the current checkout copy. The historical installed ROS Python package was removed
for the policy test's explicit installed-versus-source layout check; node tests load
the current fixture source. Browser dependencies installed in the disposable container.
This is a test environment, **not the released image or S5 hardware**.

Initial failures retained in local `/tmp/opencode/role2-*` receipts included missing
browser system libraries, old setuptools/packaging, old rosbags, source/config path
setup, and a stale hard-coded backend 1.0.0 assertion. The version assertion now
compares the actual package version. Required full browser tests are not waived by
the initial failures or the host's missing Open3D skips.

Final check counts and command receipts are recorded in `CHECKS.md` after completion.
Integrity check: 36 sealed files, digest
`db3f588df59184ad703436996f72bd94a91eca91dfcfe4a02655fcdd4397d751`;
parameters in sync; checkout version 1.1.0. Existing deck audit: 16 slides,
963 words, max 80; explicit shell-off gate parity passes. No final deck rebuild
or release-labelled media generation is claimed.
