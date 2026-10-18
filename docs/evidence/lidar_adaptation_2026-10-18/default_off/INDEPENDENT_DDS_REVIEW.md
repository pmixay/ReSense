# Independent current-image / DDS review

The selected `cecab1b` image passes the independent read-only review. The local
`resense:lidar-cecab1b` tag resolves to image
`sha256:eb53df868b1614937dcacda6dca2e37d32746a70b81f1dde030b8b2bc6b0ae02`,
matching the completed actual DDS execution receipt.

[The image review receipt](dds_independent_image_review.json) records an actual
inspection from `/` inside the image, so the installed package is checked rather
than accidentally importing the source checkout. All 28 installed package Python
and model files match the immutable source; all 43 image-provenance source files
also match. The installed Python 3.10 native binary matches the execution receipt.
Its ABI-specific hash is intentionally different from the host Python 3.12 binary.
Class, standalone YAML and installed ROS YAML all select zero replay frames.

The existing comparator was read and rerun against both retained gzip captures.
Its result is byte-identical to the producer's comparison:
[140 unique frame payloads match](dds_independent_payload_comparison.json), with
zero frame/control mismatches. All 40 Pandar and 100 actual Falcon frames are
included. Only measured time/rate/resource fields are removed from frame payloads;
decisions, health severity/messages, freshness validity/reasons, ranges, model,
gauge, detections, warnings, reset generations, drop counts and held-STOP fields
remain compared. Raw logs and report hashes were independently matched to the
completed execution receipt after decompression.

Non-frame publications have a narrower comparison: duplicate selected safety
states are collapsed and their transitions are compared. This checks watchdog /
error decisions, held STOP, validity/reason, profiles, generations and range/gauge
validity fields. It does not establish equality of every watchdog diagnostic or
of publication frequency. No new detector or player replay was performed for this
review, and no new performance claim is made.

Full offline gate, X3 and complete-recording Falcon acceptance remain separate
checks on the same selected source. This review alone does not authorize a seal.
