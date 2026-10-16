# Completed-H3 audit adapter correction — before repeat

The replacement gate has now completed with exit 0 and external finalization
`stage=ready`. The first independent offline H3 audit exited 1 at
`audit.py:155`, `assert before == after ...`, before reading frame results.
The input files have different **metadata schemas**: `source_before.json`
includes `commit`, LF/commit checks and clone-alternates information;
`source_after.json` includes `native_ignored`. Their 36-file maps, HEAD, clean
Git status and source digests are identical. Whole-object equality was an adapter
mistake, not evidence of changed source.

Repeat the audit after explicitly comparing those four shared identity fields,
requiring the before-run commit/LF checks and authenticating **both** 36-file maps
against the reviewed Git blobs. All frame, range, candidate and metric assertions
stay intact. No detector/gate/probe rerun, tolerance or production change.
