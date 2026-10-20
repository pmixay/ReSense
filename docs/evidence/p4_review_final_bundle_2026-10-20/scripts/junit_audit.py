"""Recount a JUnit file: tests, passes, failures, skips and the failure messages (first 200 characters)."""
import collections
import sys
import xml.etree.ElementTree as ET

for f in sys.argv[1:]:
    t = ET.parse(f).getroot()
    c = collections.Counter()
    fails = []
    for tc in t.iter("testcase"):
        st = "passed"
        for ch in tc:
            if ch.tag in ("failure", "error"):
                st = ch.tag
                fails.append((tc.get("classname"), tc.get("name"), (ch.get("message") or "")[:200].replace("\n", " ")))
            elif ch.tag == "skipped":
                st = "skipped"
        c[st] += 1
    print(f"{f}: {dict(c)}")
    for x in fails:
        print("   FAIL", x)
