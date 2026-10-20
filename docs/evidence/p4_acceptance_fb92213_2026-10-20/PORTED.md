# Ported copy (20.10 evening, P1)

Source: branch `claude/trusting-dirac-ywtapy` at `12bcbf9` (P4), copied unchanged; this note is the only addition.

* **What it measured:** `fb92213` = `f56ad5e` plus `resense/lowobj.py` of the **F1a completion**. That completion was rejected by an independent review
  ([review](../f1a_completion_review_2026-10-20/README.md)) and **reverted** by the captain ([`DECISIONS.md`](../../DECISIONS.md) row 47); the shipped frozen files are those of
  `f56ad5e` again (`detector_freeze.py verify` PASS on the R3 seal). P4 knows about the revert.
* **What this means for the verdict:** "no blocking finding on the measured source" is about the neighbouring source, not an acceptance of the shipped bytes. The shipped bytes
  are covered by P4's independent final-bundle review of `f56ad5e` (PR #50, [`../p4_review_final_bundle_2026-10-20/`](../p4_review_final_bundle_2026-10-20/README.md)).
  What still carries over from this run: P4's own statement that every changed gate row comes from the completion, i.e. the rest of the bundle is unchanged against `cc6226e`
  (strict gate, X3 0 of 260, whole Falcon 4,443 rows).
* **Where it disagrees with the review that led to the revert:** P4's README (section "The F1a change, line by line", item 3) shows that the surface excludes the footprints of low clusters;
  the review's finding F1 is about the object's own upper returns that lie outside every low footprint. P4 did not build the synthetic approach scenes in which that occurs.
