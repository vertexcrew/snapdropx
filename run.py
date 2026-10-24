import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import uvicorn

from snapdropx.main import app

if __name__ == "__main__":
    # Serves on port 8000 by default; override with PORT if set.
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
