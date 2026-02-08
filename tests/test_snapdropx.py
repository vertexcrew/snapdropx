"""Test suite for Skyhook security and functionality."""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from skyhook.security import parse_auth_string, sanitize_path
from skyhook.server import create_app


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
        with pytest.raises(ValueError, match="Invalid auth format"):
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])