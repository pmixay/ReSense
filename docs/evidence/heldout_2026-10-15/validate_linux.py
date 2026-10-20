#!/usr/bin/env python3
"""Run the registered ``validate.py`` on a LF checkout (Linux), changing nothing that is registered.

The registration (15.10) fingerprinted the three judge shell scripts on a Windows checkout, i.e. with CRLF line ends;
a Linux checkout has LF and ``validate.py`` stops with "harness input definitions changed". The three files are the same
content: the SHA-256 of their bytes with every LF turned into CRLF equals the stored value for all three (checked
20.10, ``p4_review_final_bundle_2026-10-20``). This wrapper makes exactly that one comparison on the CRLF form and
then calls ``validate.main()`` unchanged. ``spec.json``, ``input_metadata.json`` and ``validate.py`` are not edited.

    python3 -B validate_linux.py --self-test [--check-inputs --data-root <root> --original-root <ride root>]

``--check-inputs`` compares the file fingerprints with ``spec.json`` paths (Windows paths of the registration machine):
give the Linux locations with ``--data-root`` / ``--original-root``; it reads names and timestamp files only.
"""
import hashlib
import sys
from pathlib import Path

import validate

_definition_hashes = validate.definition_hashes


def definition_hashes_crlf(spec):
    directory = validate.ROOT / spec["source_definition_directory"]
    hashes = _definition_hashes(spec)                       # also checks the five interval definitions in the matrix
    for name in hashes:
        raw = (directory / name).read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        hashes[name] = hashlib.sha256(raw).hexdigest()
    return hashes


validate.definition_hashes = definition_hashes_crlf

if __name__ == "__main__":
    sys.exit(validate.main())
