# Role 2 owner handoffs — 16 October 2026

**Superseding captain decision, 17.10:** the request below for an 8-physical-core host is no
longer a prerequisite. Available-hardware measurements, including 2–4 cores, are acceptable
with resources and results recorded; no performance extrapolation is an acceptance result.
The captain handles GitHub quota/billing and release is deferred until CI is fixed.
The dated handoff below is retained as history; current S5 instructions are in BACKLOG.

Base: `cfae4ba9334df6912c9e2c336dea4eb1c1865935`, branch `role-2`.
User authorized the coordinated webapp/backend and marker-text changes **for P1 review**.
No external inputs beyond the repository were supplied. This file records requests,
not messages dispatched to team members or approvals received.

## P1 — integration, permitted release, demo and host

* Review the consumer/backend additive metadata flow and RViz marker text. Marker
  explanations use `evaluate_decision` on the same projected result as before; policy,
  defaults, ranges, freshness and latch rules in the producer are unchanged.
* Confirm O1: allowed version and defence duration. Fetch still exposes only v1.0.0;
  selected 1.1.0 remains sealed/unreleased. Supply H6/E1 receipt, archive/checksum,
  source/tag/image ID and selected demo device before new release-labelled media.
* Assign an idle ≥8 **physical** core host/operator by 21.10. This host is
  i5-8250U, 1 socket ×4 cores ×2 threads, not S5 hardware. No booking is claimed.
* Lead actual 19.10/22.10 rehearsals; provide second device and final PDF/speech approval.
  Confirm release-match and repeat affected checks after any version swap.

## P4 — numeric export agreement and durable evidence

**Update:** handoff `6d6aaca` received and independently checked; see
[P4 intake](P4_INTAKE.md). Current register/export, raw archive and limitations
are delivered. P2 accepts the proposed export as its chart-input basis. The
requests below record the earlier handoff; release J1 remains pending on H6/E1.

Latest fetched evaluation tip: `a33eabddeb139500971d888b2b7e513cb6091e68`.
Its `rejudge_2026-10-16/README.md` says **J1 prepared / dry run PASS; release J1 not run**.
The prerelease 2,488-frame comparison is unscored, not a new 1.1.0 score. No P4
branch was merged into this consumer branch, and no final chart values were inferred.

Please approve the Role 2 plan §5 handoff and export existing JSON/CSV files plus a
complete case register. Include full measured SHA, seal, release/image, scorer/protocol,
recording, geometry, dimensions, real/organizer-synthetic/team-synthetic, in-sample/held-out,
first STOP, held-90% definition/value, visible/matched counts, units, null reasons and
limitations. Export every row, including failures. Preserve **B=roundT_doubleT** and
**C=roundT_pressureGate_roundT**; separate cache gate and node-decoded measurements.

The new `scripts/p2_chart_sources.py` is a **P2-local draft reference checker**, not
an imposed P4 API. It reads existing JSON via file/hash/JSON-pointer references,
checks complete declared case coverage and ≥3 geometries, keeps misses/nulls, and
produces a full-table SVG plus common JSON input for later deck/video cards.
`build_deck.py --check-node-source <declaration> --render-node-chart <directory>`
uses it without rebuilding the deck. Final mode additionally requires recorded
P1/P4 approval, verified release and available raw evidence. It does not establish
that self-declared review fields are authentic; the linked human review is required.

The declaration fields are documented in `load_sources`; test-only examples are in
`tests/test_p2_chart_sources.py`. No numeric production declaration is created before
agreement. Once agreed, add X3 comparisons, false STOP episodes/time/km, counts and
clock-specific timing cards from the same export; do not turn the full-table draft
into a slide without the ≤80-word/≥3-geometry design and visual review.

The P4 handoff leaves raw JSONL in `/home/user/rs-data/j1/` in an ephemeral container.
Please export a durable archive with checksum and restoration instructions **before
retirement**. A hash index without retrievable files does not close numeric parity.

Residual D1 owner correction: DATASET's dual-return assertion needs P4 correction
against the 13.10 judgement (193→189 STOP frames; platform CAUTION 51→11%).
EXPERIMENTS changes and geometric interpretations require P3/P4 review.

## P3 — limitations for final captions

Keep the inherited High tall-object miss visible; free-top was withdrawn. The
selected A-axis probe is 82/177, not the historical withdrawn 157-frame gain.
H2 C-person 82.77 m / 55 STOP frames is one synthetic probe, not general recall.
The monitored-range cap does not solve the curved-axis limitation. R1/R2 screens,
S1 and runtime C1-v2 failed acceptance and must stay labelled as rejected attempts.

## Media / S5 preflight to complete with the owners

The existing overview measures 180.000000 s, H.264 1920×1080 at 25 fps, AAC audio.
It is historical media. Keep names/photos and template slides 7–11; final range
charts, captions/voice and a new fallback wait for permitted release and numeric inputs.

Before S5: record topology/affinity/quotas/RAM, native backend, Python/NumPy,
background load, sequential disk throughput (~225 MB/s 360° demand), input hashes,
DDS/player settings and cold/warm procedure. Verify archive, inspect exact image,
deliberately alias that ID to `resense:latest`, record previous alias and ID before/after,
then run `SKIP_BUILD=1 bash scripts/bench_8core.sh <360-bag> <120-bag>` on matching source.
Run **360°/120° × literal/README ×3** separately under the existing
[S1 Docker protocol](../node_startup_2026-10-15/DOCKER_PROTOCOL.md), after P1/P4 agree
the final-image adaptation. Console smoke tests are not this matrix.

Retain every run, p50/p95/max/FPS, fresh/processed/input, source age, first-STOP lag,
STOP frames, skips/drops and CPU/RSS. S5 README 360° targets: p95 ≤80 ms and fresh
≥195/201, explicit PASS/FAIL; also report the original BACKLOG S1 thresholds.
No local 4-core timings, simulation FPS or core-count extrapolation can close S5.
