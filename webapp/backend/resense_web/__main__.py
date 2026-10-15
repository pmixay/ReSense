"""``python -m resense_web [--host H] [--port P] [--reload] [--timeout-keep-alive S]``: serve the
API (and the built frontend) with uvicorn."""
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
    p.add_argument("--timeout-keep-alive", type=int, default=settings.keep_alive_s, metavar="S",
                   help=f"close an idle connection after S seconds (default {settings.keep_alive_s}; behind a "
                        "reverse proxy keep it above the proxy's idle timeout)")
    args = p.parse_args(argv)

    import uvicorn
    uvicorn.run("resense_web.app:create_app", factory=True, host=args.host, port=args.port,
                reload=args.reload, reload_dirs=[str(PACKAGE_DIR)] if args.reload else None,
                log_level=args.log_level, timeout_keep_alive=max(1, args.timeout_keep_alive))
    return 0


if __name__ == "__main__":
    sys.exit(main())
