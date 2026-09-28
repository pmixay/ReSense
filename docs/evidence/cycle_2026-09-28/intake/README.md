# Fresh local cache intake

The original six directory bags and all 1,510 set O frames were converted again at
full rate. The complete original ride archive was streamed through the production
intake code using a local-file adapter (included here). All 221 splits / 11,271
frames were newly cached; no historical subset was reused. Size and SHA256 match
the retained published archive metadata. The archive itself was not downloaded
again. No claim of a new recording or new holdout data is made.

Encoding is centimetre compact16, with recorded timestamps, individually compressed
NPY files. Binary data remains outside Git at `ReSense-cycle-data/cache`; the
manifest records encoding, coverage and timestamp gaps. Full gate outputs identify
the source commit and effective configuration. The six-bag/set O intake records
frame coverage; this packet does not claim those raw files were independently
rehashed again in this run.
