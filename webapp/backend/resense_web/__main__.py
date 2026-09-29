"""``python -m resense_web [--host H] [--port P] [--reload]``: serve the API (and the built
frontend) with uvicorn."""
from __future__ import annotations

import argparse
import sys

from resense_web.settings import PACKAGE_DIR, get_settings


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    p = argparse.ArgumentParser(prog="python -m resense_web", description="ReSense web backend (FastAPI)")
    p.add_argument("--host", default=settings.host, help=f"bind address (default {settings.host})")
    p.add_argument("--port", type=int, default=settings.port, help=f"port (default {settings.port})")
    p.add_argument("--reload", action="store_true", help="restart on code changes (development)")
    p.add_argument("--log-level", default="info")
    args = p.parse_args(argv)

    import uvicorn
    uvicorn.run("resense_web.app:create_app", factory=True, host=args.host, port=args.port,
                reload=args.reload, reload_dirs=[str(PACKAGE_DIR)] if args.reload else None,
                log_level=args.log_level)
    return 0


if __name__ == "__main__":
    sys.exit(main())
