"""CLI entrypoint for SnapDropX file server."""

from pathlib import Path
from typing import Optional

import typer
import uvicorn

from snapdropx.security import generate_self_signed_cert, parse_auth_string
from snapdropx.server import SnapDropXServer


app = typer.Typer(
    name="snapdropx",
    help="🚀 SnapDropX – Secure, zero-config file drop server",
    add_completion=False,
)


@app.command()
def serve(
    path: Path = typer.Argument(
        Path("."),
        help="Directory to serve",
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
):
    """
    Start the SnapDropX file server.
    """

    # =========================
    # Parse authentication
    # =========================
    username = None
    password = None
    if auth:
        try:
            username, password = parse_auth_string(auth)
        except ValueError as e:
            typer.echo(f"❌ Error: {e}", err=True)
            raise typer.Exit(1)

    # =========================
    # SSL handling
    # =========================
    ssl_certfile = None
    ssl_keyfile = None
    if ssl:
        typer.echo("🔐 Generating self-signed SSL certificate...")
        ssl_certfile, ssl_keyfile = generate_self_signed_cert()
        typer.echo("✅ SSL certificate generated")

    # =========================
    # Startup info
    # =========================
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

    # =========================
    # Create FastAPI app
    # =========================
    server = SnapDropXServer(path, username, password)
    fastapi_app = server.app

    # =========================
    # Run server
    # =========================
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


@app.command()
def version():
    """Show SnapDropX version."""
    typer.echo("SnapDropX v1.0.0")


if __name__ == "__main__":
    app()
