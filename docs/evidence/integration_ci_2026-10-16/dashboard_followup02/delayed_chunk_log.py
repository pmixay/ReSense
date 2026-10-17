"""Diagnostic backend launcher: delay one real chunk-2 success log, never its response/data."""
import logging
import os
from pathlib import Path
import re
import runpy
import threading
import time


def main():
    release = Path(os.environ["UPLOAD_BOUNDARY_RELEASE"])
    original = logging.Logger.handle

    def handle(logger, record):
        text = record.getMessage()
        if logger.name == "uvicorn.access" and re.search(r'"PUT /api/uploads/[^/]+/chunked/2\?[^" ]* HTTP/1.1" 200', text):
            def deliver():
                deadline = time.monotonic() + 90
                while not release.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                original(logger, record)
            threading.Thread(target=deliver, daemon=True).start()
        else:
            original(logger, record)

    logging.Logger.handle = handle
    runpy.run_module("resense_web", run_name="__main__")


if __name__ == "__main__":
    main()
