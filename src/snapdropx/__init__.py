"""
SnapDropX
=========

SnapDropX is a secure, zero-configuration file server with upload capabilities.
It provides a modern CLI interface and a FastAPI-powered backend for quickly
sharing files over HTTP/HTTPS with optional authentication.

Author: SnapDropX Contributors
License: MIT
"""

# =========================
# Package Metadata
# =========================
__title__ = "snapdropx"
__version__ = "1.0.0"
__author__ = "SnapDropX Contributors"
__license__ = "MIT"
__description__ = (
    "A secure, zero-config file drop server with upload capabilities "
    "and encrypted transport"
)

# =========================
# Public API Exports
# =========================
from .main import app as cli_app
from .server import create_app
__all__ = ["cli_app", "create_app"]
__all__ = [
    "cli_app",
    "create_app",
    "__title__",
    "__version__",
    "__author__",
    "__license__",
    "__description__",
]
