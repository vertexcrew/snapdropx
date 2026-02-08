"""FastAPI application for SnapDropX file server."""

import mimetypes
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from snapdropx.security import AuthManager, sanitize_path


# =========================
# Utility Functions
# =========================
def format_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


# =========================
# Server Class
# =========================
class SnapDropXServer:
    """Main SnapDropX file server application."""

    def __init__(
        self,
        serve_path: Path,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.serve_path = serve_path.resolve()
        self.auth_manager = AuthManager(username, password)

        self.app = FastAPI(
            title="SnapDropX File Server",
            description="Secure, zero-config file drop server",
            version="1.0.0",
        )

        base_dir = Path(__file__).resolve().parent

        # =========================
        # Static files
        # =========================
        self.app.mount(
            "/static",
            StaticFiles(directory=base_dir / "static"),
            name="static",
        )

        # =========================
        # Templates
        # =========================
        self.templates = Jinja2Templates(
            directory=str(base_dir / "templates")
        )

        # Register custom filter
        self.templates.env.filters["format_size"] = format_size

        # Register routes
        self._register_routes()

    # =========================
    # Routes
    # =========================
    def _register_routes(self):
        @self.app.get("/", response_class=HTMLResponse)
        async def index(
            request: Request,
            path: str = "",
            authorized: bool = Depends(self.auth_manager.verify_credentials),
        ):
            return await self.list_directory(request, path)

        @self.app.get("/browse/{path:path}", response_class=HTMLResponse)
        async def browse(
            request: Request,
            path: str,
            authorized: bool = Depends(self.auth_manager.verify_credentials),
        ):
            return await self.list_directory(request, path)

        @self.app.get("/download/{path:path}")
        async def download(
            path: str,
            authorized: bool = Depends(self.auth_manager.verify_credentials),
        ):
            return await self.download_file(path)

        @self.app.post("/upload")
        async def upload(
            files: List[UploadFile] = File(...),
            path: str = "",
            authorized: bool = Depends(self.auth_manager.verify_credentials),
        ):
            return await self.upload_files(files, path)

        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "version": "1.0.0"}

    # =========================
    # Directory Listing
    # =========================
    async def list_directory(
        self, request: Request, path: str = ""
    ) -> HTMLResponse:
        target_path = sanitize_path(self.serve_path, path)

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")

        if not target_path.is_dir():
            return await self.download_file(path)

        items = []
        for item in sorted(
            target_path.iterdir(),
            key=lambda x: (not x.is_dir(), x.name.lower()),
        ):
            try:
                stat = item.stat()
                items.append(
                    {
                        "name": item.name,
                        "is_dir": item.is_dir(),
                        "size": stat.st_size if item.is_file() else 0,
                        "modified": datetime.fromtimestamp(stat.st_mtime),
                        "path": str(item.relative_to(self.serve_path)),
                    }
                )
            except (OSError, PermissionError):
                continue

        breadcrumbs = []
        if path:
            parts = Path(path).parts
            for i, part in enumerate(parts):
                breadcrumbs.append(
                    {
                        "name": part,
                        "path": "/".join(parts[: i + 1]),
                    }
                )

        return self.templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "items": items,
                "current_path": path,
                "breadcrumbs": breadcrumbs,
                "auth_enabled": self.auth_manager.enabled,
                "format_size": format_size,  # ✅ FIXED
            },
        )

    # =========================
    # Download
    # =========================
    async def download_file(self, path: str) -> FileResponse:
        file_path = sanitize_path(self.serve_path, path)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        mime_type, _ = mimetypes.guess_type(str(file_path))

        return FileResponse(
            path=file_path,
            media_type=mime_type or "application/octet-stream",
            filename=file_path.name,
        )

    # =========================
    # Upload
    # =========================
    async def upload_files(
        self, files: List[UploadFile], path: str = ""
    ) -> dict:
        target_dir = sanitize_path(self.serve_path, path)

        if not target_dir.exists() or not target_dir.is_dir():
            raise HTTPException(
                status_code=400,
                detail="Invalid upload directory",
            )

        uploaded, errors = [], []

        for file in files:
            try:
                safe_name = Path(file.filename).name
                if not safe_name or safe_name.startswith("."):
                    raise ValueError("Invalid filename")

                file_path = target_dir / safe_name
                with open(file_path, "wb") as f:
                    while chunk := await file.read(1024 * 1024):
                        f.write(chunk)

                uploaded.append(
                    {
                        "filename": safe_name,
                        "size": file_path.stat().st_size,
                    }
                )
            except Exception as e:
                errors.append(
                    {"filename": file.filename, "error": str(e)}
                )

        return {
            "uploaded": uploaded,
            "errors": errors,
            "success": len(uploaded),
            "failed": len(errors),
        }


# =========================
# App Factory
# =========================
def create_app(
    serve_path: Path,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> FastAPI:
    """Create and configure the SnapDropX application."""
    return SnapDropXServer(
        serve_path, username, password
    ).app
