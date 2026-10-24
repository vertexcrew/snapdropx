"""FastAPI application for SnapDropX file server."""

import io
import mimetypes
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

from snapdropx.security import AuthManager, sanitize_path

__version__ = "2.0.0"

# File suffixes treated as previewable text (in addition to text/* MIME types).
TEXT_SUFFIXES = {
    ".txt", ".md", ".json", ".csv", ".log", ".py", ".js", ".html",
    ".css", ".xml", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".sh",
}

# Max size (bytes) for inline text previews.
PREVIEW_TEXT_MAX_BYTES = 2 * 1024 * 1024


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


def _validate_simple_name(name: str) -> str:
    """Validate a single path component (no slashes, no dot-files)."""
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid name")
    if "/" in name or "\\" in name:
        raise HTTPException(
            status_code=400, detail="Name must not contain slashes"
        )
    if name.startswith("."):
        raise HTTPException(
            status_code=400, detail="Name must not start with a dot"
        )
    return name


class RenameRequest(BaseModel):
    path: str
    new_name: str


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
        max_upload_mb: float = 100,
    ):
        self.serve_path = serve_path.resolve()
        self.auth_manager = AuthManager(username, password)
        self.max_upload_mb = max_upload_mb
        self.max_upload_bytes = int(max_upload_mb * 1024 * 1024)

        self.app = FastAPI(
            title="SnapDropX File Server",
            description="Secure, zero-config file drop server",
            version="2.0.0",
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

        @self.app.get("/preview/{path:path}")
        async def preview(
            path: str,
            authorized: bool = Depends(self.auth_manager.verify_credentials),
        ):
            return await self.preview_file(path)

        @self.app.get("/zip")
        async def zip_root(
            authorized: bool = Depends(self.auth_manager.verify_credentials),
        ):
            return await self.zip_directory("")

        @self.app.get("/zip/{path:path}")
        async def zip_dir(
            path: str,
            authorized: bool = Depends(self.auth_manager.verify_credentials),
        ):
            return await self.zip_directory(path)

        @self.app.post("/upload")
        async def upload(
            files: List[UploadFile] = File(...),
            path: str = Form(""),
            authorized: bool = Depends(self.auth_manager.verify_credentials),
        ):
            return await self.upload_files(files, path)

        @self.app.delete("/delete/{path:path}")
        async def delete(
            path: str,
            authorized: bool = Depends(self.auth_manager.verify_credentials),
        ):
            return await self.delete_path(path)

        @self.app.post("/mkdir")
        async def mkdir(
            path: str = Form(""),
            name: str = Form(...),
            authorized: bool = Depends(self.auth_manager.verify_credentials),
        ):
            return await self.make_directory(path, name)

        @self.app.post("/rename")
        async def rename(
            body: RenameRequest,
            authorized: bool = Depends(self.auth_manager.verify_credentials),
        ):
            return await self.rename_path(body.path, body.new_name)

        @self.app.get("/api/files")
        async def api_files(
            path: str = "",
            authorized: bool = Depends(self.auth_manager.verify_credentials),
        ):
            items = self.list_items(path)
            return {"path": path, "items": items}

        @self.app.get("/api/stats")
        async def api_stats(
            authorized: bool = Depends(self.auth_manager.verify_credentials),
        ):
            return self.compute_stats()

        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "version": "2.0.0"}

    # =========================
    # Directory Listing
    # =========================
    def list_items(self, path: str = "") -> list:
        """Return the listing dicts for a directory (shared by HTML + API)."""
        target_path = sanitize_path(self.serve_path, path)

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")

        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

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
        return items

    def compute_stats(self) -> dict:
        """Walk the served tree and summarise counts and total size."""
        files = 0
        folders = 0
        total_size = 0
        for item in self.serve_path.rglob("*"):
            try:
                if item.is_dir():
                    folders += 1
                elif item.is_file():
                    files += 1
                    total_size += item.stat().st_size
            except (OSError, PermissionError):
                continue
        return {
            "files": files,
            "folders": folders,
            "total_size": total_size,
            "total_size_human": format_size(total_size),
        }

    async def list_directory(
        self, request: Request, path: str = ""
    ) -> HTMLResponse:
        target_path = sanitize_path(self.serve_path, path)

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")

        if not target_path.is_dir():
            return await self.download_file(path)

        items = self.list_items(path)

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
            request,
            "index.html",
            {
                "items": items,
                "current_path": path,
                "breadcrumbs": breadcrumbs,
                "auth_enabled": self.auth_manager.enabled,
                "format_size": format_size,  # ✅ FIXED
            },
        )

    # =========================
    # Download / Preview
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

    async def preview_file(self, path: str):
        """Serve a file inline for preview, falling back to download."""
        file_path = sanitize_path(self.serve_path, path)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"
        inline_headers = {
            "Content-Disposition": f'inline; filename="{file_path.name}"'
        }

        if mime_type.startswith("image/"):
            return FileResponse(
                path=file_path,
                media_type=mime_type,
                headers=inline_headers,
            )

        if (
            mime_type.startswith("text/")
            or file_path.suffix.lower() in TEXT_SUFFIXES
        ) and file_path.stat().st_size <= PREVIEW_TEXT_MAX_BYTES:
            try:
                text = file_path.read_bytes().decode("utf-8")
            except (UnicodeDecodeError, OSError):
                return await self.download_file(path)
            return PlainTextResponse(text, headers=inline_headers)

        # Anything else: fall back to a normal download.
        return await self.download_file(path)

    # =========================
    # Zip
    # =========================
    async def zip_directory(self, path: str = "") -> StreamingResponse:
        target_path = sanitize_path(self.serve_path, path)

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")

        if not target_path.is_file() and not target_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        if target_path.is_file():
            raise HTTPException(
                status_code=400, detail="Cannot zip a file, only directories"
            )

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in sorted(target_path.rglob("*")):
                if item.is_file():
                    zf.write(item, item.relative_to(target_path))
        buffer.seek(0)

        archive_name = (
            f"{target_path.name}.zip" if path else "files.zip"
        )
        return StreamingResponse(
            buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{archive_name}"'
            },
        )

    # =========================
    # Upload
    # =========================
    def _unique_path(self, target_dir: Path, name: str) -> Path:
        """Never overwrite: name.ext -> name (1).ext, name (2).ext, ..."""
        stem = Path(name).stem
        suffix = Path(name).suffix
        candidate = target_dir / name
        counter = 1
        while candidate.exists():
            candidate = target_dir / f"{stem} ({counter}){suffix}"
            counter += 1
        return candidate

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
            file_path = None
            try:
                safe_name = Path(file.filename).name
                if not safe_name or safe_name.startswith("."):
                    raise ValueError("Invalid filename")

                file_path = self._unique_path(target_dir, safe_name)
                total = 0
                with open(file_path, "wb") as f:
                    while chunk := await file.read(1024 * 1024):
                        total += len(chunk)
                        if total > self.max_upload_bytes:
                            raise HTTPException(
                                status_code=413,
                                detail=(
                                    f"File exceeds the {self.max_upload_mb:g} MB "
                                    "upload limit"
                                ),
                            )
                        f.write(chunk)

                uploaded.append(
                    {
                        "filename": file_path.name,
                        "size": file_path.stat().st_size,
                    }
                )
            except HTTPException as e:
                if file_path is not None and file_path.exists():
                    file_path.unlink(missing_ok=True)
                errors.append(
                    {"filename": file.filename, "error": e.detail}
                )
            except Exception as e:
                if file_path is not None and file_path.exists():
                    file_path.unlink(missing_ok=True)
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
    # Delete / Mkdir / Rename
    # =========================
    async def delete_path(self, path: str) -> dict:
        target = sanitize_path(self.serve_path, path)

        if not target.exists():
            raise HTTPException(status_code=404, detail="Path not found")

        if target.is_dir():
            if any(target.iterdir()):
                raise HTTPException(
                    status_code=400,
                    detail="Directory is not empty",
                )
            target.rmdir()
        else:
            target.unlink()

        return {"deleted": True, "path": path}

    async def make_directory(self, path: str, name: str) -> dict:
        _validate_simple_name(name)
        parent = sanitize_path(self.serve_path, path)

        if not parent.exists() or not parent.is_dir():
            raise HTTPException(
                status_code=400, detail="Invalid parent directory"
            )

        new_dir = parent / name
        if new_dir.exists():
            raise HTTPException(
                status_code=400, detail="A file or folder with that name exists"
            )
        new_dir.mkdir()

        rel = str(new_dir.relative_to(self.serve_path))
        return {"created": True, "name": name, "path": rel}

    async def rename_path(self, path: str, new_name: str) -> dict:
        _validate_simple_name(new_name)
        target = sanitize_path(self.serve_path, path)

        if not target.exists():
            raise HTTPException(status_code=404, detail="Path not found")

        dest = target.parent / new_name
        if dest.exists():
            raise HTTPException(
                status_code=400, detail="A file or folder with that name exists"
            )
        target.rename(dest)

        rel = str(dest.relative_to(self.serve_path))
        return {
            "renamed": True,
            "old_path": path,
            "new_path": rel,
            "path": rel,
        }


# =========================
# App Factory
# =========================
def create_app(
    serve_path: Path,
    username: Optional[str] = None,
    password: Optional[str] = None,
    max_upload_mb: float = 100,
) -> FastAPI:
    """Create and configure the SnapDropX application."""
    return SnapDropXServer(
        serve_path, username, password, max_upload_mb=max_upload_mb
    ).app
