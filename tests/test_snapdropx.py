"""Test suite for SnapDropX security and functionality."""

import io
import tempfile
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from snapdropx.security import parse_auth_string, sanitize_path
from snapdropx.server import create_app


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        
        # Create test files and directories
        (temp_path / "test.txt").write_text("Hello, World!")
        (temp_path / "subdir").mkdir()
        (temp_path / "subdir" / "nested.txt").write_text("Nested file")
        
        yield temp_path


@pytest.fixture
def app_no_auth(temp_dir):
    """Create app without authentication."""
    return create_app(temp_dir)


@pytest.fixture
def app_with_auth(temp_dir):
    """Create app with authentication."""
    return create_app(temp_dir, username="testuser", password="testpass")


@pytest.fixture
def client_no_auth(app_no_auth):
    """Test client without authentication."""
    return TestClient(app_no_auth)


@pytest.fixture
def client_with_auth(app_with_auth):
    """Test client with authentication."""
    return TestClient(app_with_auth)


class TestSecurity:
    """Test security features."""
    
    def test_parse_auth_string_valid(self):
        """Test parsing valid auth string."""
        username, password = parse_auth_string("user:pass")
        assert username == "user"
        assert password == "pass"
    
    def test_parse_auth_string_with_colon_in_password(self):
        """Test parsing auth string with colon in password."""
        username, password = parse_auth_string("user:pass:word")
        assert username == "user"
        assert password == "pass:word"
    
    def test_parse_auth_string_invalid_format(self):
        """Test parsing invalid auth string."""
        with pytest.raises(ValueError, match="Auth format must be username:password"):
            parse_auth_string("invalid")
    
    def test_parse_auth_string_empty_username(self):
        """Test parsing auth string with empty username."""
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_auth_string(":password")
    
    def test_parse_auth_string_empty_password(self):
        """Test parsing auth string with empty password."""
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_auth_string("username:")
    
    def test_sanitize_path_valid(self, temp_dir):
        """Test sanitizing valid paths."""
        # Valid paths should work
        result = sanitize_path(temp_dir, "test.txt")
        assert result == temp_dir / "test.txt"
        
        result = sanitize_path(temp_dir, "subdir/nested.txt")
        assert result == temp_dir / "subdir" / "nested.txt"
    
    def test_sanitize_path_directory_traversal(self, temp_dir):
        """Test that directory traversal is blocked."""
        from fastapi import HTTPException
        
        # These should all raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            sanitize_path(temp_dir, "../../../etc/passwd")
        assert exc_info.value.status_code == 403
        
        with pytest.raises(HTTPException):
            sanitize_path(temp_dir, "subdir/../../etc/passwd")
        
        with pytest.raises(HTTPException):
            sanitize_path(temp_dir, "./../../etc/passwd")
    
    def test_sanitize_path_absolute_path(self, temp_dir):
        """Test that absolute paths outside base are blocked."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException):
            sanitize_path(temp_dir, "/etc/passwd")


class TestAuthentication:
    """Test authentication functionality."""
    
    def test_no_auth_access(self, client_no_auth):
        """Test accessing server without authentication when auth is disabled."""
        response = client_no_auth.get("/")
        assert response.status_code == 200
    
    def test_auth_required(self, client_with_auth):
        """Test that authentication is required when enabled."""
        response = client_with_auth.get("/")
        assert response.status_code == 401
    
    def test_auth_valid_credentials(self, client_with_auth):
        """Test access with valid credentials."""
        response = client_with_auth.get(
            "/",
            auth=("testuser", "testpass")
        )
        assert response.status_code == 200
    
    def test_auth_invalid_credentials(self, client_with_auth):
        """Test access with invalid credentials."""
        response = client_with_auth.get(
            "/",
            auth=("testuser", "wrongpass")
        )
        assert response.status_code == 401
        
        response = client_with_auth.get(
            "/",
            auth=("wronguser", "testpass")
        )
        assert response.status_code == 401


class TestFileOperations:
    """Test file listing and download operations."""
    
    def test_list_root_directory(self, client_no_auth, temp_dir):
        """Test listing root directory."""
        response = client_no_auth.get("/")
        assert response.status_code == 200
        assert b"test.txt" in response.content
        assert b"subdir" in response.content
    
    def test_list_subdirectory(self, client_no_auth):
        """Test listing subdirectory."""
        response = client_no_auth.get("/browse/subdir")
        assert response.status_code == 200
        assert b"nested.txt" in response.content
    
    def test_download_file(self, client_no_auth):
        """Test downloading a file."""
        response = client_no_auth.get("/download/test.txt")
        assert response.status_code == 200
        assert response.content == b"Hello, World!"
    
    def test_download_nonexistent_file(self, client_no_auth):
        """Test downloading a file that doesn't exist."""
        response = client_no_auth.get("/download/nonexistent.txt")
        assert response.status_code == 404
    
    def test_browse_nonexistent_directory(self, client_no_auth):
        """Test browsing a directory that doesn't exist."""
        response = client_no_auth.get("/browse/nonexistent")
        assert response.status_code == 404


class TestFileUpload:
    """Test file upload functionality."""
    
    def test_upload_single_file(self, client_no_auth, temp_dir):
        """Test uploading a single file."""
        files = {"files": ("upload.txt", b"Upload test content", "text/plain")}
        response = client_no_auth.post("/upload", files=files)
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == 1
        assert result["failed"] == 0
        
        # Verify file was created
        uploaded_file = temp_dir / "upload.txt"
        assert uploaded_file.exists()
        assert uploaded_file.read_text() == "Upload test content"
    
    def test_upload_multiple_files(self, client_no_auth, temp_dir):
        """Test uploading multiple files."""
        files = [
            ("files", ("file1.txt", b"Content 1", "text/plain")),
            ("files", ("file2.txt", b"Content 2", "text/plain")),
        ]
        response = client_no_auth.post("/upload", files=files)
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == 2
        assert result["failed"] == 0
        
        # Verify files were created
        assert (temp_dir / "file1.txt").exists()
        assert (temp_dir / "file2.txt").exists()
    
    def test_upload_with_auth(self, client_with_auth, temp_dir):
        """Test uploading requires authentication when enabled."""
        files = {"files": ("auth_upload.txt", b"Auth test", "text/plain")}
        
        # Without auth should fail
        response = client_with_auth.post("/upload", files=files)
        assert response.status_code == 401
        
        # With auth should succeed
        response = client_with_auth.post(
            "/upload",
            files=files,
            auth=("testuser", "testpass")
        )
        assert response.status_code == 200


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_endpoint(self, client_no_auth):
        """Test health check endpoint."""
        response = client_no_auth.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestNewEndpoints:
    """Tests for the v2 endpoints: delete, mkdir, rename, preview, zip, API."""

    def test_delete_file(self, client_no_auth, temp_dir):
        response = client_no_auth.delete("/delete/test.txt")
        assert response.status_code == 200
        assert response.json()["deleted"] is True
        assert not (temp_dir / "test.txt").exists()

    def test_delete_empty_directory(self, client_no_auth, temp_dir):
        (temp_dir / "empty").mkdir()
        response = client_no_auth.delete("/delete/empty")
        assert response.status_code == 200
        assert not (temp_dir / "empty").exists()

    def test_delete_nonempty_directory_refused(self, client_no_auth):
        response = client_no_auth.delete("/delete/subdir")
        assert response.status_code == 400

    def test_delete_missing_path(self, client_no_auth):
        response = client_no_auth.delete("/delete/nope.txt")
        assert response.status_code == 404

    def test_mkdir(self, client_no_auth, temp_dir):
        response = client_no_auth.post(
            "/mkdir", data={"path": "", "name": "newfolder"}
        )
        assert response.status_code == 200
        assert (temp_dir / "newfolder").is_dir()

    def test_mkdir_rejects_slashes_and_dots(self, client_no_auth):
        assert client_no_auth.post(
            "/mkdir", data={"path": "", "name": "a/b"}
        ).status_code == 400
        assert client_no_auth.post(
            "/mkdir", data={"path": "", "name": ".hidden"}
        ).status_code == 400

    def test_rename_file(self, client_no_auth, temp_dir):
        response = client_no_auth.post(
            "/rename", json={"path": "test.txt", "new_name": "renamed.txt"}
        )
        assert response.status_code == 200
        assert response.json()["new_path"] == "renamed.txt"
        assert (temp_dir / "renamed.txt").exists()
        assert not (temp_dir / "test.txt").exists()

    def test_rename_rejects_bad_name(self, client_no_auth):
        response = client_no_auth.post(
            "/rename", json={"path": "test.txt", "new_name": "../evil"}
        )
        assert response.status_code == 400

    def test_preview_text_inline(self, client_no_auth):
        response = client_no_auth.get("/preview/test.txt")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert "inline" in response.headers["content-disposition"]
        assert response.text == "Hello, World!"

    def test_preview_image_inline(self, client_no_auth, temp_dir):
        # Minimal 1x1 PNG.
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
            "0000000a49444154789c6360000000020001e221bc330000000049454e44ae426082"
        )
        (temp_dir / "dot.png").write_bytes(png)
        response = client_no_auth.get("/preview/dot.png")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/png")
        assert "inline" in response.headers["content-disposition"]

    def test_preview_binary_falls_back_to_download(self, client_no_auth, temp_dir):
        (temp_dir / "blob.bin").write_bytes(bytes(range(256)))
        response = client_no_auth.get("/preview/blob.bin")
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]

    def test_zip_directory(self, client_no_auth):
        response = client_no_auth.get("/zip/subdir")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            assert "nested.txt" in zf.namelist()

    def test_zip_root(self, client_no_auth):
        response = client_no_auth.get("/zip")
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            assert "test.txt" in zf.namelist()

    def test_zip_file_refused(self, client_no_auth):
        response = client_no_auth.get("/zip/test.txt")
        assert response.status_code == 400

    def test_api_files(self, client_no_auth):
        response = client_no_auth.get("/api/files", params={"path": "subdir"})
        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "subdir"
        names = [item["name"] for item in data["items"]]
        assert "nested.txt" in names

    def test_api_stats(self, client_no_auth):
        response = client_no_auth.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["files"] == 2  # test.txt + subdir/nested.txt
        assert data["folders"] == 1
        assert data["total_size"] > 0
        assert data["total_size_human"]

    def test_upload_duplicate_name_renumbered(self, client_no_auth, temp_dir):
        files = {"files": ("test.txt", b"Second copy", "text/plain")}
        response = client_no_auth.post("/upload", files=files)
        assert response.status_code == 200
        uploaded = response.json()["uploaded"]
        assert uploaded[0]["filename"] == "test (1).txt"
        assert (temp_dir / "test (1).txt").read_text() == "Second copy"
        # Original untouched.
        assert (temp_dir / "test.txt").read_text() == "Hello, World!"

    def test_upload_into_subfolder_via_form_path(self, client_no_auth, temp_dir):
        files = {"files": ("inner.txt", b"Inner", "text/plain")}
        response = client_no_auth.post(
            "/upload", files=files, data={"path": "subdir"}
        )
        assert response.status_code == 200
        assert (temp_dir / "subdir" / "inner.txt").exists()

    def test_upload_oversize_rejected(self, temp_dir):
        app = create_app(temp_dir, max_upload_mb=0.001)  # ~1 KB cap
        client = TestClient(app)
        files = {"files": ("big.txt", b"x" * 4096, "text/plain")}
        response = client.post("/upload", files=files)
        assert response.status_code == 200
        result = response.json()
        assert result["failed"] == 1
        assert "exceeds" in result["errors"][0]["error"]
        assert not (temp_dir / "big.txt").exists()

    def test_new_endpoints_require_auth(self, client_with_auth):
        assert client_with_auth.delete("/delete/test.txt").status_code == 401
        assert client_with_auth.get("/api/stats").status_code == 401
        response = client_with_auth.get(
            "/api/stats", auth=("testuser", "testpass")
        )
        assert response.status_code == 200


class TestAuthGatesEveryRoute:
    """When auth is on, NO file-serving route may answer anonymously.

    This is the deployment guarantee: a public instance protected by
    SNAPDROPX_AUTH must reject unauthenticated visitors on every route
    that touches files, not just the HTML pages.
    """

    @pytest.mark.parametrize(
        "method,url",
        [
            ("GET", "/"),
            ("GET", "/browse/subdir"),
            ("GET", "/download/test.txt"),
            ("GET", "/preview/test.txt"),
            ("GET", "/zip"),
            ("GET", "/zip/subdir"),
            ("GET", "/api/files"),
            ("GET", "/api/stats"),
            ("DELETE", "/delete/test.txt"),
        ],
    )
    def test_unauthenticated_get_delete_rejected(
        self, client_with_auth, method, url
    ):
        response = client_with_auth.request(method, url)
        assert response.status_code == 401

    @pytest.mark.parametrize("url", ["/upload", "/mkdir", "/rename"])
    def test_unauthenticated_posts_rejected(self, client_with_auth, url):
        if url == "/upload":
            response = client_with_auth.post(
                url, files={"files": ("x.txt", b"x", "text/plain")}
            )
        elif url == "/mkdir":
            response = client_with_auth.post(
                url, data={"path": "", "name": "newdir"}
            )
        else:
            response = client_with_auth.post(
                url, json={"path": "test.txt", "new_name": "y.txt"}
            )
        assert response.status_code == 401

    def test_authenticated_file_routes_work(self, client_with_auth):
        auth = ("testuser", "testpass")
        assert client_with_auth.get("/download/test.txt", auth=auth).status_code == 200
        assert client_with_auth.get("/preview/test.txt", auth=auth).status_code == 200
        assert client_with_auth.get("/zip/subdir", auth=auth).status_code == 200
        assert client_with_auth.get("/api/files", auth=auth).status_code == 200

    def test_health_stays_public(self, client_with_auth):
        # /health is deliberately unauthenticated: platform health checks
        # (Render etc.) need it, and it exposes no file data.
        assert client_with_auth.get("/health").status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])