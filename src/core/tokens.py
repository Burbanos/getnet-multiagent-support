"""Short-lived HS256 JWT access tokens with signing key rotation (stdlib only)."""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
import uuid
from typing import Any

from src.config import settings
from src.core.auth import ROLES, Principal

DEV_JWT_KID = "dev"
DEV_JWT_SECRET = "getnet-dev-jwt-signing-key-do-not-use-in-production-0001"
LEEWAY_S = 30
REQUIRED_CLAIMS = ("iss", "aud", "sub", "role", "key_id", "iat", "nbf", "exp", "jti")


class TokenError(ValueError):
    """Raised when an access or refresh token is invalid, expired, revoked, or reused."""

    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or f"Token validation failed: {reason}")


def parse_signing_keys(spec: str) -> dict[str, str]:
    """Parse 'kid:secret;kid:secret' into {kid: secret}, requiring secrets >= 32 chars."""
    raw = str(spec or "").strip()
    if not raw:
        return {}
    entries = [entry.strip() for entry in raw.split(";") if entry.strip()]
    if not entries:
        raise ValueError("Invalid JWT_SIGNING_KEYS format (expected kid:secret;...)")

    keys: dict[str, str] = {}
    for entry in entries:
        if ":" not in entry:
            raise ValueError("Invalid JWT_SIGNING_KEYS entry (expected kid:secret)")
        kid, secret = entry.split(":", 1)
        kid = kid.strip()
        if not kid or any(ch.isspace() for ch in kid):
            raise ValueError("Invalid key ID in JWT_SIGNING_KEYS")
        if len(secret) < 32:
            raise ValueError("JWT_SIGNING_KEYS secret must be at least 32 characters")
        if kid in keys:
            raise ValueError(f"Duplicate kid in JWT_SIGNING_KEYS: {kid!r}")
        keys[kid] = secret
    return keys


def validate_signing_keys_config() -> None:
    """Validate JWT_SIGNING_KEYS and JWT_ACTIVE_KID; fail fast in production on missing or weak keys."""
    is_prod = settings.APP_ENV.lower() == "production"
    raw = settings.JWT_SIGNING_KEYS.strip()
    if is_prod:
        if not raw:
            raise ValueError("JWT_SIGNING_KEYS must be configured when APP_ENV=production.")
        keys = parse_signing_keys(raw)
        if DEV_JWT_KID in keys:
            raise ValueError("JWT_SIGNING_KEYS cannot use development kid 'dev' in production.")
        for secret in keys.values():
            if hmac.compare_digest(secret, DEV_JWT_SECRET):
                raise ValueError("JWT_SIGNING_KEYS cannot use the development signing secret in production.")
        active_kid = settings.JWT_ACTIVE_KID.strip()
        if not active_kid or active_kid not in keys:
            raise ValueError("JWT_ACTIVE_KID must identify an active key in JWT_SIGNING_KEYS.")
        return

    if raw:
        keys = parse_signing_keys(raw)
        active_kid = settings.JWT_ACTIVE_KID.strip()
        if active_kid and active_kid not in keys:
            raise ValueError("JWT_ACTIVE_KID must identify an active key in JWT_SIGNING_KEYS.")


def _resolve_signing_table() -> tuple[dict[str, str], str | None]:
    raw = settings.JWT_SIGNING_KEYS.strip()
    if not raw:
        if settings.APP_ENV.lower() == "production":
            return {}, None
        return {DEV_JWT_KID: DEV_JWT_SECRET}, DEV_JWT_KID

    keys = parse_signing_keys(raw)
    active_kid = settings.JWT_ACTIVE_KID.strip()
    if not active_kid:
        if settings.APP_ENV.lower() != "production" and len(keys) == 1:
            active_kid = next(iter(keys))
        else:
            active_kid = ""
    return keys, active_kid or None


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    if not segment or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in segment):
        raise ValueError("Invalid base64url segment")
    pad = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode((segment + pad).encode("ascii"))


def _sign_hs256(signing_input: bytes, secret: str) -> bytes:
    return hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()


def issue_access_token(principal: Principal, now: float | None = None) -> tuple[str, int]:
    """Issue a signed HS256 JWT access token for principal, returning (token, expires_in_seconds)."""
    if principal.role not in ROLES:
        raise ValueError(f"Unsupported role for access token: {principal.role!r}")
    keys, active_kid = _resolve_signing_table()
    if not keys or not active_kid or active_kid not in keys:
        raise ValueError("JWT_SIGNING_KEYS and JWT_ACTIVE_KID must be configured to issue access tokens.")

    secret = keys[active_kid]
    ttl = int(settings.ACCESS_TOKEN_TTL_S)
    iat = int(time.time() if now is None else now)
    header = {"alg": "HS256", "typ": "JWT", "kid": active_kid}
    claims: dict[str, Any] = {
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "sub": principal.user_id,
        "role": principal.role,
        "key_id": principal.key_id,
        "iat": iat,
        "nbf": iat,
        "exp": iat + ttl,
        "jti": uuid.uuid4().hex,
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    claims_b64 = _b64url_encode(json.dumps(claims, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    signing_input = f"{header_b64}.{claims_b64}".encode("ascii")
    sig_b64 = _b64url_encode(_sign_hs256(signing_input, secret))
    return f"{header_b64}.{claims_b64}.{sig_b64}", ttl


def _is_numeric_date(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def decode_access_token(token: str, now: float | None = None) -> Principal:
    """Verify HS256 JWT access token and return Principal, raising TokenError on any failure."""
    if not isinstance(token, str) or not token.strip():
        raise TokenError("malformed")
    parts = token.strip().split(".")
    if len(parts) != 3 or not all(parts):
        raise TokenError("malformed")

    header_b64, claims_b64, sig_b64 = parts
    try:
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        claims = json.loads(_b64url_decode(claims_b64).decode("utf-8"))
        actual_sig = _b64url_decode(sig_b64)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error) as exc:
        raise TokenError("malformed") from exc

    if not isinstance(header, dict) or not isinstance(claims, dict):
        raise TokenError("malformed")

    if header.get("alg") != "HS256":
        raise TokenError("bad_algorithm")

    kid = header.get("kid")
    try:
        keys, _ = _resolve_signing_table()
    except ValueError as exc:
        raise TokenError("unknown_kid") from exc
    if not isinstance(kid, str) or kid not in keys:
        raise TokenError("unknown_kid")

    signing_input = f"{header_b64}.{claims_b64}".encode("ascii")
    expected_sig = _sign_hs256(signing_input, keys[kid])
    if not hmac.compare_digest(actual_sig, expected_sig):
        raise TokenError("bad_signature")

    if any(k not in claims for k in REQUIRED_CLAIMS):
        raise TokenError("malformed")

    for str_key in ("iss", "aud", "sub", "role", "key_id", "jti"):
        val = claims.get(str_key)
        if not isinstance(val, str) or not val.strip():
            raise TokenError("malformed")

    for num_key in ("iat", "nbf", "exp"):
        if not _is_numeric_date(claims.get(num_key)):
            raise TokenError("malformed")

    if claims["iss"] != settings.JWT_ISSUER:
        raise TokenError("bad_issuer")
    if claims["aud"] != settings.JWT_AUDIENCE:
        raise TokenError("bad_audience")
    if claims["role"] not in ROLES:
        raise TokenError("bad_role")

    cur = float(time.time() if now is None else now)
    if cur > float(claims["exp"]) + LEEWAY_S:
        raise TokenError("expired")
    if cur < float(claims["nbf"]) - LEEWAY_S:
        raise TokenError("not_yet_valid")

    return Principal(
        user_id=str(claims["sub"]),
        role=str(claims["role"]),
        key_id=str(claims["key_id"]),
    )
