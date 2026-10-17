# N5 labeling and C2 acceptance execution — 17 October 2026

Work started from live `main` at
`3b7d7aa7cbbf238c21f84330497697da131b7cb9`, after syncing the machine checkout.
The remote branch
[`work/n5-labels-c2-acceptance`](https://github.com/pmixay/ReSense/tree/work/n5-labels-c2-acceptance)
was created and pushed before implementation. The captain requested team labeling
of the missing N5 data, C2 acceptance, available-hardware measurements, and release
deferral until CI is repaired.

## Delivered evidence

- [N5 labels and scoring](../n5_labels_2026-10-17/README.md): complete frame coverage
  of the platform, switch and tunnels recordings, with reviewed object geometry,
  explicit uncertainty and an independent scorer. The platform extension has an
  exact-reference control. Missing organizer annotations no longer prevent team
  annotation and scoring.
- [C2 implementation and acceptance](../c2_acceptance_2026-10-17/README.md): shared
  node/offline conservative range calculation, canonical-data scorer, two explicit
  overclaim definitions, original and revised acceptance results, local tests and
  independent review. The captain approved conservative ranges with measured loss;
  the accepted profile retains at least 65% of each empty-bag median. The original
  90% criterion remains visibly failed. Historical intended-gauge residuals remain
  reported rather than being erased by the measured-envelope definition.
- Hardware and release plans now permit available hardware, including 2–4 cores.
  The captain owns GitHub billing/quota; no release was made by this work.

The standalone P1 dependency map is stored outside the repository at
`/home/resense/P1_work_map_2026-10-17.md`, as requested. It is not a repository artifact.

## Machine and data identity

This machine exposes **one CPU**, affinity `[0]`, and about **4 GB RAM**.
[environment.json](environment.json), [lscpu.txt](lscpu.txt) and
[memory.txt](memory.txt) record the actual resources. The native detector extension
is loaded; numerical checks use one BLAS/OMP thread and the Haswell OpenBLAS path.
No 2-, 4- or 8-core performance result is inferred from this host.

[data_intake.json](data_intake.json) records the verified SHA-256 and byte size of
the three downloaded archives, the decoder identity and range filter, every cache
metadata hash, and every decoded frame hash. Complete caches contain:

| Input | Frames |
| --- | ---: |
| synthetic_platform | 386 |
| synthetic_switch | 736 |
| synthetic_tunnels | 545 |
| cloud_with_fake_obj / Set O | 1,510 |
| Original six comparison recordings | 2,488 |
| **Total** | **5,665** |

Archives and decoded frames remain outside the repository under
`/home/resense/data`. Temporary extracted DB3 copies were removed only after the
verified archive and complete decoded cache were retained. Labels, reproduction
inputs, review images, scores and small provenance records are the repository
artifacts; raw bags are not committed.

## Validation scope

The C2 record contains the full local test result, affected-code checks after the
captain's acceptance decision, exact pinned lint, parameter-copy verification,
decision/detection preservation checks, and the unchanged 36-file detector seal.
N5 records independent reference checks, complete frame-key validation, geometric
matching with uncertainty bounds and scorer tests.

The node tests exercise its real Python class with ROS transport/message stand-ins.
This machine did not run a new Docker/DDS playback or released-image acceptance.
The explicit accepted conservative profile is available for configured Pandar
operation; changing the default launch remains part of release integration.
Unknown/Falcon profiles do not inherit a Pandar density model. Local checks do not
replace repaired GitHub CI or the later release checks.

## Clarification of item 2 in the P1 map

The organizer questions were whether an updated version may be used at the defence
or re-evaluation, the pitch/Q&A duration, and the required demo format. They do not
block this development branch. No message was sent to organizers or other team
members by this task.
