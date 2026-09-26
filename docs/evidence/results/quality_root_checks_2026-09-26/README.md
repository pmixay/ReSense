# Main branch checks after freshness integration

The full suite passed **667 core/tool tests, 14 browser tests and six subtests**. One browser
test failed because the live expiry timer changed an already-invalid result's diagnostic reason
between delivery and assertion. The UI correctly remained FAULT. Commit `f66e982` reads the
rejection reason in the same browser task as delivery; it changes the test, not product behavior.
The complete affected browser suite then passed **15/15**.

The [receipt](receipt.json) records both invocations, counts and source identity. Initial failure
logs and JUnit output remain compressed here. This is combined evidence from the full run and
the corrected browser suite; it is not reported as one all-green invocation.

The original detector seal and archived candidate-evidence hashes pass. These checks cover the
main branch's P3d core and freshness controls. M2 remains an unaccepted candidate, and the separate
zero-alarm runtime failure remains open. CI and any later detector candidate have their own
acceptance records.
