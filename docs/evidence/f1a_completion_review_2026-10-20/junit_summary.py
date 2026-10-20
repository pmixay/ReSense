#!/usr/bin/env python3
"""Reviewer script: summarise pytest JUnit XML files (counts, failures, errors, skips with reasons).

    python junit_summary.py <file.xml> [<file.xml> ...]
"""
import sys
import xml.etree.ElementTree as ET

for path in sys.argv[1:]:
    root = ET.parse(path).getroot()
    suites = list(root.iter("testsuite"))
    tot = {k: sum(int(s.get(k, 0)) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
    bad = [(c.get("classname"), c.get("name")) for c in root.iter("testcase")
           if c.find("failure") is not None or c.find("error") is not None]
    skipped = {}
    for c in root.iter("testcase"):
        s = c.find("skipped")
        if s is not None:
            skipped[s.get("message", "")[:90]] = skipped.get(s.get("message", "")[:90], 0) + 1
    print(path.split("/")[-1], tot, "passed", tot["tests"] - tot["failures"] - tot["errors"] - tot["skipped"])
    for b in bad:
        print("   FAIL/ERROR", b)
    for m, n in skipped.items():
        print("   skipped", n, m)
