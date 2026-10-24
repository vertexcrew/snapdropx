"""Vercel serverless entrypoint for SnapDropX.

Vercel runs Python as serverless functions, not as a long-running uvicorn
server, so the FastAPI app is wrapped with Mangum. The served directory
defaults to /tmp/snapdropx-data (the only writable path on Vercel) and is
seeded with a welcome file on first start when empty.

NOTE: files on Vercel are ephemeral — uploads live only while the function
instance is warm and may disappear at any time. For a permanent file server
use the Render/Docker deployment (see render.yaml). Vercel is best for a
browse / preview / download demo.
"""

import os
from pathlib import Path

# Must be set BEFORE importing snapdropx.main, which reads it at import time.
os.environ.setdefault("SNAPDROPX_DIR", "/tmp/snapdropx-data")

from mangum import Mangum  # noqa: E402

from snapdropx.main import app  # noqa: E402

DATA_DIR = Path(os.environ["SNAPDROPX_DIR"])
DATA_DIR.mkdir(parents=True, exist_ok=True)
welcome = DATA_DIR / "README.txt"
if not welcome.exists():
    welcome.write_text(
        "Welcome to SnapDropX on Vercel!\n\n"
        "Browse, preview and download files from this demo.\n"
        "Note: uploads on this demo deployment are temporary and may "
        "disappear — for permanent storage use the Render deployment.\n"
    )


class StripApiPrefixMiddleware:
    """Strip Vercel's rewrite destination from the request path.

    vercel.json rewrites every path to /api/index.py, and on Vercel the
    app can receive that rewritten path (e.g. /api/index.py or
    /api/index.py/health) instead of the original URL. FastAPI has no route
    for it, so every request answered {"detail": "Not Found"}. Stripping
    the prefix restores the original path (/ or /health) before routing.

    IMPORTANT: the middleware wraps `app` itself, not just the Mangum
    handler — Vercel's Python runtime serves the module's `app` object
    directly, so a wrapper applied only to `handler` never runs on Vercel
    (that is why the first attempt changed nothing live). Local requests
    never look like the cases below, so this is a no-op outside Vercel.
    """

    def __init__(self, wrapped_app):
        self.wrapped_app = wrapped_app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            path = scope.get("path", "")
            if path == "/api/index.py" or path.startswith("/api/index.py/"):
                stripped = path[len("/api/index.py"):] or "/"
                scope = {**scope, "path": stripped, "raw_path": stripped.encode()}
            elif path in ("/api", "/api/", "/index.py"):
                scope = {**scope, "path": "/", "raw_path": b"/"}
        await self.wrapped_app(scope, receive, send)


# Wrap the app itself: Vercel serves this `app` object directly.
app = StripApiPrefixMiddleware(app)
handler = Mangum(app)
