"""
Security and authentication functions (passwords and JWT-like HMAC tokens).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

SECRET_KEY = os.getenv("SECRET_KEY", "tubecut_secret_key_change_me_in_production_123456")


def hash_password(password: str) -> str:
    """Hash password using PBKDF2 with SHA256."""
    salt = os.urandom(16)
    rounds = 100000
    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    stored = f"pbkdf2_sha256${rounds}${base64.b64encode(salt).decode('utf-8')}${base64.b64encode(derived_key).decode('utf-8')}"
    return stored


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against PBKDF2 hash."""
    try:
        parts = hashed.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        rounds = int(parts[1])
        salt = base64.b64decode(parts[2])
        original_hash = base64.b64decode(parts[3])
        derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
        return hmac.compare_digest(derived_key, original_hash)
    except Exception:
        return False


def create_access_token(data: dict, expires_in: int = 3600 * 24 * 7) -> str:
    """Generate a signed access token."""
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_in
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def decode_access_token(token: str) -> dict | None:
    """Verify and decode a signed token."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        padding = "=" * (4 - len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode((payload_b64 + padding).encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None
