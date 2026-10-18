"""Opt-in, fail-closed process startup for the external N2 input stress harness."""

import os

if os.environ.get("RESENSE_N2_PROXY") == "1":
    try:
        from proxy_input_hook import install

        install()
    except BaseException:
        import traceback

        traceback.print_exc()
        # Python otherwise prints and ignores a sitecustomize exception, which
        # could silently produce an untransformed Set F child process.
        os._exit(86)
