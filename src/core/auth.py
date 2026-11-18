"""Authentication, credential principal resolution, and rate limiting."""
from __future__ import annotations

import getpass
import hashlib
import hmac
import math
import sys
from dataclasses import dataclass

import redis
from fastapi import Header, HTTPException

from src.config import settings
from src.core.rate_limit import RateLimiter, RedisRateLimiter

ROLES = ("customer", "operator")

DEV_API_KEYS: dict[str, tuple[str, str]] = {
    "getnet-dev-key": ("cliente1988", "customer"),
    "getnet-dev-operator": ("operador_dev", "operator"),
}


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: str
    key_id: str


def hash_api_key(key: str) -> str:
    """Return SHA-256 hex digest of the UTF-8 encoded key."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def parse_api_keys(spec: str) -> dict[str, Principal]:
    """
    Parse an API_KEYS specification string.

    Format: hash:user_id:role;hash:user_id:role;...
    Raises ValueError on invalid hash length/casing, empty user_id, invalid role, or duplicates.
    """
    table: dict[str, Principal] = {}
    entries = [entry.strip() for entry in spec.split(";") if entry.strip()]

    for entry in entries:
        parts = entry.split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid API key entry format (expected hash:user_id:role): {entry!r}")

        h = parts[0].strip()
        user_id = parts[1].strip()
        role = parts[2].strip()

        if len(h) != 64 or not all(c in "0123456789abcdef" for c in h):
            raise ValueError(f"Invalid hash format (must be 64 lowercase hex characters): {h!r}")

        if not user_id:
            raise ValueError(f"user_id cannot be empty in entry: {entry!r}")

        if role not in ROLES:
            raise ValueError(f"Invalid role {role!r} (must be one of {ROLES}): {entry!r}")

        if h in table:
            raise ValueError(f"Duplicate API key hash in specification: {h!r}")

        table[h] = Principal(
            user_id=user_id,
            role=role,
            key_id=h[:12],
        )

    return table


def auth_mode() -> str:
    """Determine the active authentication mode from configuration."""
    raw_keys = settings.API_KEYS.strip()
    if bool(raw_keys):
        try:
            parse_api_keys(raw_keys)
            return "configured"
        except ValueError:
            return "invalid"
    if settings.APP_ENV.lower() == "production":
        return "none"
    return "development_defaults"


def validate_auth_config() -> str:
    """
    Validate authentication configuration on startup.
    Raises ValueError if API_KEYS is malformed, otherwise returns active auth_mode.
    """
    get_principal_table()
    return auth_mode()


def get_principal_table() -> dict[str, Principal]:
    """
    Resolve principal lookup table based on current settings.
    - configured: parsed from settings.API_KEYS (raises ValueError if malformed)
    - none: empty table (all requests will be rejected)
    - development_defaults: default dev customer and operator keys
    """
    if bool(settings.API_KEYS.strip()):
        return parse_api_keys(settings.API_KEYS)
    if settings.APP_ENV.lower() == "production":
        return {}
    # development_defaults
    table: dict[str, Principal] = {}
    for raw_key, (user_id, role) in DEV_API_KEYS.items():
        h = hash_api_key(raw_key)
        table[h] = Principal(user_id=user_id, role=role, key_id=h[:12])
    return table


_rate_limiter_instance: RateLimiter | RedisRateLimiter | None = None


def get_rate_limiter() -> RateLimiter | RedisRateLimiter:
    """Return the global rate limiter singleton (Redis when REDIS_URL is set, else local memory)."""
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        redis_url = settings.REDIS_URL.strip()
        if redis_url:
            client = redis.Redis.from_url(
                redis_url,
                socket_timeout=0.5,
                socket_connect_timeout=0.5,
            )
            _rate_limiter_instance = RedisRateLimiter(
                client,
                settings.RATE_LIMIT_PER_MINUTE,
                prefix=settings.RATE_LIMIT_REDIS_PREFIX,
            )
        else:
            _rate_limiter_instance = RateLimiter(limit_per_minute=settings.RATE_LIMIT_PER_MINUTE)
    return _rate_limiter_instance


def reset_rate_limiter() -> None:
    """Reset the global RateLimiter singleton."""
    global _rate_limiter_instance
    _rate_limiter_instance = None


def authenticate(x_api_key: str | None = Header(None, alias="X-API-Key")) -> Principal:
    """
    FastAPI dependency to authenticate requests using X-API-Key header.
    Validates against principal table and enforces rate limit.
    """
    try:
        table = get_principal_table()
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail="Authentication misconfigured: check API_KEYS.",
        ) from exc

    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing or invalid API key.")

    incoming_hash = hash_api_key(x_api_key)

    matched: Principal | None = None
    for key_hash, principal in table.items():
        if hmac.compare_digest(incoming_hash, key_hash):
            matched = principal
            break

    if matched is None:
        raise HTTPException(status_code=401, detail="Missing or invalid API key.")

    wait = get_rate_limiter().hit(matched.key_id)
    if wait is not None:
        retry_after = str(max(1, math.ceil(wait)))
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": retry_after},
        )

    return matched


def main() -> None:
    """CLI utility to hash an API key without printing the plaintext."""
    if len(sys.argv) > 1 and sys.argv[1] == "hash":
        try:
            key = getpass.getpass("API Key: ")
        except (EOFError, KeyboardInterrupt):
            sys.exit(1)
        print(hash_api_key(key))
    else:
        print("Usage: python -m src.core.auth hash", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
