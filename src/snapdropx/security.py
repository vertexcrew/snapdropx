"""Security utilities for SnapDropX including auth and SSL certificate generation."""

import os
import secrets
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# HTTP Basic auth handler
security = HTTPBasic()


class AuthManager:
    """Manages HTTP Basic Authentication."""

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.username = username
        self.password = password
        self.enabled = bool(username and password)

    def verify_credentials(
        self,
        credentials: HTTPBasicCredentials = Depends(security),
    ) -> bool:
        """Verify HTTP Basic Auth credentials."""
        if not self.enabled:
            return True

        username_ok = secrets.compare_digest(
            credentials.username,
            self.username,
        )
        password_ok = secrets.compare_digest(
            credentials.password,
            self.password,
        )

        if not (username_ok and password_ok):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )

        return True


# =========================
# Path Sanitization
# =========================
def sanitize_path(base_path: Path, requested_path: str) -> Path:
    requested_path = requested_path.lstrip("/")
    full_path = (base_path / requested_path).resolve()

    try:
        full_path.relative_to(base_path.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied (path traversal)",
        )

    return full_path


# =========================
# SSL Certificate
# =========================
def generate_self_signed_cert() -> Tuple[str, str]:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SnapDropX"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost")]
            ),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    cert_fd, cert_path = tempfile.mkstemp(suffix=".crt")
    key_fd, key_path = tempfile.mkstemp(suffix=".key")

    with os.fdopen(cert_fd, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    with os.fdopen(key_fd, "wb") as f:
        f.write(
            private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )

    return cert_path, key_path


# =========================
# Auth String Parser
# =========================
def parse_auth_string(auth: str) -> Tuple[str, str]:
    if ":" not in auth:
        raise ValueError("Auth format must be username:password")

    user, pwd = auth.split(":", 1)
    if not user or not pwd:
        raise ValueError("Username/password cannot be empty")

    return user, pwd
