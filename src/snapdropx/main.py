"""CLI entrypoint for SnapDropX file server."""

import os
from pathlib import Path
from typing import Optional

import typer
import uvicorn

from snapdropx.security import generate_self_signed_cert, parse_auth_string
from snapdropx.server import SnapDropXServer

__version__ = "2.0.0"


def _env_config():
    """Read deployment config from the environment.

    SNAPDROPX_DIR: directory to serve (default ".").
    SNAPDROPX_AUTH: "username:password" or empty (default: no auth).
    SNAPDROPX_MAX_UPLOAD_MB: per-file upload cap in MB (default 100).
    NOTE: SNAPDROPX_PORT is intentionally NOT read here — it is only
    for the uvicorn command line (e.g. the Dockerfile / Procfile), which
    binds the port itself.
    """
    serve_dir = Path(os.environ.get("SNAPDROPX_DIR", "."))
    username = None
    password = None
    auth_str = os.environ.get("SNAPDROPX_AUTH", "")
    if auth_str:
        try:
            username, password = parse_auth_string(auth_str)
        except ValueError:
            username, password = None, None
    try:
        max_upload_mb = float(
            os.environ.get("SNAPDROPX_MAX_UPLOAD_MB", "100")
        )
    except ValueError:
        max_upload_mb = 100.0
    return serve_dir, username, password, max_upload_mb


# =========================================
# FastAPI app for Render/Vercel deployment
# =========================================
_env_dir, _env_user, _env_pass, _env_max_mb = _env_config()
server = SnapDropXServer(
    _env_dir, _env_user, _env_pass, max_upload_mb=_env_max_mb
)
app = server.app


# =========================================
# Typer CLI app
# =========================================
cli = typer.Typer(
    name="snapdropx",
    help="🚀 SnapDropX – Secure, zero-config file drop server",
    add_completion=False,
)


def _serve_impl(
    path: Optional[Path] = None,
    port: int = 8000,
    host: str = "0.0.0.0",
    auth: Optional[str] = None,
    ssl: bool = False,
    reload: bool = False,
    max_upload_mb: Optional[float] = None,
):
    """Core server startup, shared by `snapdropx serve` and bare `snapdropx`.
    """
    # No path argument given -> fall back to SNAPDROPX_DIR, then ".".
    if path is None:
        path = Path(os.environ.get("SNAPDROPX_DIR", ".")).resolve()

    username = None
    password = None

    # CLI flags win; fall back to the environment for auth / upload cap.
    if auth:
        try:
            username, password = parse_auth_string(auth)
        except ValueError as e:
            typer.echo(f"❌ Error: {e}", err=True)
            raise typer.Exit(1)
    elif os.environ.get("SNAPDROPX_AUTH"):
        try:
            username, password = parse_auth_string(
                os.environ["SNAPDROPX_AUTH"]
            )
        except ValueError as e:
            typer.echo(f"❌ Error: {e}", err=True)
            raise typer.Exit(1)

    if max_upload_mb is None:
        try:
            max_upload_mb = float(
                os.environ.get("SNAPDROPX_MAX_UPLOAD_MB", "100")
            )
        except ValueError:
            max_upload_mb = 100.0

    ssl_certfile = None
    ssl_keyfile = None

    if ssl:
        typer.echo("🔐 Generating self-signed SSL certificate...")
        ssl_certfile, ssl_keyfile = generate_self_signed_cert()
        typer.echo("✅ SSL certificate generated")

    protocol = "https" if ssl else "http"

    typer.echo("")
    typer.echo("🚀 Starting SnapDropX")
    typer.echo("─" * 50)
    typer.echo(f"📁 Serving: {path.absolute()}")
    typer.echo(f"🌐 URL: {protocol}://{host}:{port}")

    if username:
        typer.echo(f"🔒 Auth: Enabled (user: {username})")
    else:
        typer.echo("🔓 Auth: Disabled (public access)")

    typer.echo("─" * 50)
    typer.echo("💡 Press Ctrl+C to stop")
    typer.echo("")

    server = SnapDropXServer(
        path, username, password, max_upload_mb=max_upload_mb
    )
    fastapi_app = server.app

    try:
        uvicorn.run(
            fastapi_app,
            host=host,
            port=port,
            ssl_certfile=ssl_certfile,
            ssl_keyfile=ssl_keyfile,
            reload=reload,
            log_level="info",
        )

    except KeyboardInterrupt:
        typer.echo("\n👋 Shutting down SnapDropX")
        raise typer.Exit(0)

    finally:
        if ssl_certfile:
            Path(ssl_certfile).unlink(missing_ok=True)

        if ssl_keyfile:
            Path(ssl_keyfile).unlink(missing_ok=True)


@cli.callback(invoke_without_command=True)
def _callback(ctx: typer.Context):
    """Bare `snapdropx` (no subcommand) just starts the server."""
    if ctx.invoked_subcommand is None:
        _serve_impl()


@cli.command()
def serve(
    path: Path = typer.Argument(
        None,
        help="Directory to serve (default: env SNAPDROPX_DIR or current directory)",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    port: int = typer.Option(
        8000,
        "--port", "-p",
        help="Port to bind to",
        min=1,
        max=65535,
    ),
    host: str = typer.Option(
        "0.0.0.0",
        "--host", "-h",
        help="Host interface to bind to",
    ),
    auth: Optional[str] = typer.Option(
        None,
        "--auth", "-a",
        help="Enable authentication (format: username:password)",
    ),
    ssl: bool = typer.Option(
        False,
        "--ssl",
        help="Enable HTTPS with self-signed certificate",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reload for development",
    ),
    max_upload_mb: float = typer.Option(
        None,
        "--max-upload-mb",
        help="Per-file upload cap in MB (default: env SNAPDROPX_MAX_UPLOAD_MB or 100)",
    ),
):
    """Start the SnapDropX file server."""
    _serve_impl(path, port, host, auth, ssl, reload, max_upload_mb)


@cli.command()
def version():
    """Show SnapDropX version."""
    typer.echo("SnapDropX v2.0.0")


if __name__ == "__main__":
    cli()






