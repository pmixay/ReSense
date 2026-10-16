# P1 bounded mapped warm setup — 16 October 2026

**Local setup verdict: PASS, one original-bag setup attempt, zero playback attempts.**
This establishes the warm precondition locally; it is not a claim that Actions or
the original nine-frame runtime loss is fixed. Previous failure records are unchanged.

## New authoritative failure

Actions run **38928306547**, Docker job **117065713597**, commit
`e6cf5f2213f47945d753a0694deb7ebf21be87f7` failed before warm playback. The raw failed
step log and parsed receipt are retained under `results/original-ci-*`.

- Cold positive/clear still produced **201/252** statuses and passed; all **453**
  frames passed the input byte-parity check. The warm player was not started.
- The warm helper read **4,821,250,048 bytes**, but the final mincore observation
  found **3,222 / 1,177,063 pages missing** (12.586 MiB), so it correctly failed.
- Actual runner resources were **2 CPUs**, affinity `[0, 1]`, **8,127,928 KiB RAM**
  (~7.75 GiB), and **6,966,280 KiB MemAvailable** after setup (~6.64 GiB).
  Cgroup CPU/memory limits were `max`; CPU throttling and OOM events were zero.
- The full read took about **19.04 seconds**, while system I/O pressure increased.
  Available memory is a reclaimability estimate, not a promise that a particular
  file's pages remain resident throughout a sequential scan.

### What is and is not established about the cause

The demonstrated setup defect is that the sequential buffered-read operation did
not establish the required complete resident working set. Both the Actions receipt
and the controlled local case below directly observe that failure.

The Linux mincore implementation checks mapped PTEs or the file page cache; a lack
of permission to expose residency returns **all-one bits**, not missing-page bits.
The helper retains its ownership/CAP_FOWNER check. The observed missing bits are
therefore not explained by that permission fallback. No evidence identifies the
exact reclaim path, victim-selection decision or other process behind every missing
page on Actions. We do not assert that more RAM, extra CPUs, prior parity work, or
a production node defect caused this failure.

References inspected for these semantics:

- <https://man7.org/linux/man-pages/man2/mincore.2.html>: residency is a snapshot;
  unlocked pages can change immediately after inspection.
- <https://raw.githubusercontent.com/torvalds/linux/v6.8/mm/mincore.c>:
  `can_do_mincore`, `mincore_page`, and the all-one fallback in `do_mincore`.

## Changed method: bounded synchronous setup work

`scripts/check_warm_cache.py` now performs this fixed sequence:

1. Read each original database once, retaining byte-count and identity checks.
2. Hold **read-only** mappings of all splits and synchronously load one byte from
   every page. This performs actual page references rather than relying solely on
   buffered scanning or asynchronous `MADV_WILLNEED` hints.
3. Perform exactly one bounded repair sweep over pages that mincore currently
   reports missing. If none are missing, this sweep touches zero pages. There is
   no third sweep and no loop-until-success.
4. Release **all** setup mappings/descriptors, then independently inspect **all**
   splits again. Every page must be resident. An earlier successful sweep cannot
   replace this final check.

The setup has a fixed **60-second wall budget**, checked between reads and every
256 page touches, as well as after setup/final observation. A blocking kernel I/O
call cannot be preempted by the cooperative check, but an over-budget completion
fails and cannot produce `WARM_VERIFIED`. The work cap is one file-length read and
at most two page-touch sweeps. Resource/receipt overhead also counts in the budget.

This is bounded preparation, not a playback retry. There is no mlock, persistent
background mapper, kernel cache eviction on real data, affinity/resource-limit
change, node/default/schema change, threshold relaxation, or modified bag bytes.
The existing 100% final residency gate remains. Receipts expose the method, budget,
per-sweep before/after counts, touched pages, and mapping-release completion, plus
process identity/capabilities and global reclaim counters for diagnosis.

`dry_run.sh` changes only its method-description comment in this follow-up. The
existing boundary invocation, rate **1.0**, read-ahead **10**, discovery delay **3 s**,
positive/clear **201/252** frame requirements, **zero** drop limits, p95 **100 ms**,
minimum pace **0.9x**, and detector/node behavior are unchanged.

## Focused verification

`results/linux-contracts.txt` records **19 tests passed, zero skips** in Linux.
Tests cover fixed sweep count, touching only missing pages in the second sweep,
no writes through mappings, deadline failure before reads/page faults, closure on
error, post-setup eviction rejection, split-file final checks, unchanged bytes,
unavailable mincore, and preservation of error receipts.

A separate controlled Linux faulting check creates a **4 MiB temporary owned file**,
flushes it and evicts **only that fixture** using per-file `POSIX_FADV_DONTNEED`.
Mincore observes **0/1,024** resident pages. The actual read-only mapped setup then
establishes **1,024/1,024** residency after mappings close; file SHA-256 is unchanged.
This fixture-only eviction is never applied to the original bags or global caches.

The real Bash precondition block is also executed with a stub player: invalid
fixture exits **1 before player invocation**; a warm verified fixture invokes the
original player arguments once. Linux Bash syntax and focused **Ruff 0.15.8** pass.

## One existing read-only original-bag case

`results/bag-once/` contains the complete input, setup, delayed-boundary, console
and verdict records. The Docker invocation and source/helper/test hashes are in
`results/provenance.json`; image and volume metadata are retained separately.

- Existing volume: `rs-s1-original-bags-20261016-72a601b`, inspected first and mounted
  read-only with `volume-nocopy`. No original data or image was copied or rebuilt.
- Positive database SHA-256 matches the existing pin:
  `05f1d7f7d1bbbc5e9453877416cc9f7367c19e31d35a5291271d863fc89c5ad9`.
- The identity hash read affects initial cache state and its time is recorded.
  It is not counted as part of the method's 60-second preparation budget, just as
  CI verifies input identity before entering the warm setup.
- Existing idle web container was left running; no other process was killed and
  no hardware limit or cache-pinning policy was changed.

| Observation | Result |
| --- | ---: |
| File bytes read by setup | 4,821,250,048 |
| Total pages | 1,177,063 |
| Missing before setup | 85,384 |
| Missing after full buffered read | **62** |
| All-page mapped sweep | **1,177,063 page touches** |
| Missing after mapped sweep | **0** |
| Missing-page repair sweep | **0 page touches** |
| Final residency after all mappings close | **1,177,063 / 1,177,063** |
| Setup elapsed / budget | **30.17 / 60.00 seconds** |
| Independent observation after 3 seconds, no repair/read | **100% resident** |
| Setup attempts / playback attempts | **1 / 0** |

This is a direct before/after witness: the previous read-only preparation would
have failed on the same case's 62 missing pages; the mapped references established
full residency within the fixed budget. The repair sweep did not need to load any
pages. It is not a pass selected from repeated runs.

The local host exposes 12 CPUs and about 6.70 GiB guest RAM, not the Actions
2-CPU/7.75-GiB machine. This was setup-only, without the node workload. The kernel
can still reclaim unlocked pages later; the three-second observation proves only
this case's boundary state. **Actions still must validate this preparation with
the node present and then pass the original warm playback/runtime criteria.**
