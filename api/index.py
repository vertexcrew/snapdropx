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

handler = Mangum(app)
