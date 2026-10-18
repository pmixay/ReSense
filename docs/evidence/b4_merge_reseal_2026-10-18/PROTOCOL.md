# B4 + main integration and candidate reseal

User requested switching to `det/b4-orientation`, fetching/merging main and
resealing with verification in a clean checkout before and after native build.
Fetched main is `9917851` (PR #37); B4 tip is `6cc27be`. This record is saved
before the committed merged-source recording measurements.

Two merge conflicts combine channel-axis conflict/cadence handling with main's
orientation readiness. Both confirmation paths must set readiness and clear
conflict. A channel conflict remains a health error; actual obstacles retain
STOP priority. The search mock in the readiness test follows B4's tuple return.
New combined assertions cover the adopted mapping and health/decision contract.
Initial focused tests: 165 passed and six subtests; no recording measurements
were used to select this merge resolution.

Keep main's 1.2.0 candidate version and default configuration, including replay
opt-in. This supersedes the older B4 protocol's pre-merge 1.1.0 version choice.
The older B4 source, failures and P4 blocking review remain historical records.
This task creates a candidate integrity seal; independent P4 acceptance and
release approval are not inferred from it. The user has explicitly requested
the reseal; no release, tag or integration back into main is authorized here.

## Checks on the exact committed merged source

1. Create a detached clean worktree. Record source fingerprint and expected old
   seal rejection, build native from source, require native actually loads and
   require the fingerprint/inventory remain unchanged. Record the binary hash.
2. Run affected calibration, readiness/replay, reseed, health, native, timing,
   decision and gate/X3 tests, config sync and pinned Ruff checks. Run P4's real
   short-window reproduction on local original float32 caches with no lost
   matched STOP; retain inherited late-ring limitations.
3. Full default regression gate: six recordings, Set O, full ride, Set F;
   historical shell-off baseline; no overrides, waivers or missing rows. Verify
   all 18,329 rows and compare complete serialized non-timing output against the
   existing same-host 1.2.0 gate at `e9d8fc6`, whose frozen sources equal main.
   Additive false `orientation_conflict` metadata may be reported separately;
   no changed decisions or geometry are normalized away.
4. Fresh merged-source X3, 40 cases, unchanged battery and verified float32
   inputs, against the established raw-validated Linux 1.1 reference. Also
   compare against the previously measured default-off `cecab1b` candidate
   where possible; preserve the old identities, never relabel them as new runs.
5. Replay all 24 B4 rotations on both full empty and positive recordings for
   baseline `e9d8fc6` and merged candidate, same runtime/native and inputs. Use
   the original B4 summarizer: no wrong acceptance, no empty STOP, no GO before
   confirmation and no lost matched positive STOP versus the appropriate
   same-rotation or correctly oriented comparator. This is transformed Pandar
   coverage, not proof for physical horizontal scanners or ring-free Falcon.
6. Commit passing evidence before seal creation. Preserve all old manifests.
   Create a new candidate manifest from the committed-source gate, switch the
   default manifest, then verify the actual resulting seal in a second clean
   checkout before/after a fresh native build. Record identical fingerprints,
   binary loading, clean tracked state, manifest/evidence hashes and commands.

Use the available shared one-CPU machine, Haswell BLAS, one numerical thread
and one replay worker. Runs are serial; latency is informational. Existing
same-host baseline gate/X3 evidence is reused with explicit source/native/input
identity checks; this is not a claim of rerunning the older protocol's entire
fresh baseline/candidate gate and X3 pair. P4's final review remains pending.

## Native-build preflight amendment, before recording measurements

The standard build script produced native SHA-256 `67fa0887e5480e24ca67138ec5271969742917a5c5869d9ab4e634599d8c7394`,
whereas the previous local package build used `511f7766...`. Both pre/post-build
source fingerprints equal `68dee667f19e862913575c72fada3820199ec29cf497697cd7194b9e897f16d3`.
To avoid assuming binary equivalence, create a fresh reference checkout at
`e9d8fc6` (frozen source identical to main), build with the same script and
require identical native hashes. Run fresh reference gate and X3 before the
candidate, serially. Reference X3 must pass against the established Linux 1.1
reference, then candidate against this fresh reference. The fresh reference
gate replaces the earlier planned reused gate as the primary frame comparator.
Historical reports retain their original identities. This adds measurements
without relaxing acceptance.

## P4 merge while measurements were running

The user additionally requested merging P4 branch `ccr-027997e8-kqywat` and
deleting it. Tip `8a0af65` was merged in `eb03c98`, pushed and its remote branch
deleted only after verifying the merged history was on the target remote. All
frozen detector files remain byte-identical to the measured merge `0779db7`;
measurements continue in the detached worktree. `p4_import.json` records the
merge/deletion and verifies both imported review archives.

This append records the later instruction, not a retroactive preregistration.
The measurement criteria and native-build amendment were committed in
`008a7ec` before the recording runs. P4's no-blocker review of `0bbc6ed` and its
B1-closed/B4-X3-passing review of `6cc27be` retain their original source
identities. They do not become reviews of `0779db7` by being merged.
