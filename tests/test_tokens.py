"""Unit tests for HS256 JWT access tokens, key rotation, and credential expiry."""
from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta

import pytest

from src.config import settings
from src.core.auth import (
    DEV_API_KEYS,
    Principal,
    hash_api_key,
    is_principal_expired,
    parse_api_keys,
    validate_auth_config,
)
from src.core.tokens import (
    DEV_JWT_KID,
    DEV_JWT_SECRET,
    TokenError,
    decode_access_token,
    issue_access_token,
    parse_signing_keys,
    validate_signing_keys_config,
)

_SECRET_ALPHA = "alpha-signing-secret-material-0000000001"
_SECRET_BETA = "beta-signing-secret-material-00000000002"


def _b64u(obj: dict) -> str:
    raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def test_issue_and_decode_roundtrip_dev_fallback() -> None:
    principal = Principal(user_id="merchant_one", role="customer", key_id="dev_key_id")
    token, ttl = issue_access_token(principal, now=1_700_000_000)

    assert ttl == settings.ACCESS_TOKEN_TTL_S
    parts = token.split(".")
    assert len(parts) == 3

    pad_header = parts[0] + "=" * (-len(parts[0]) % 4)
    header = json.loads(base64.urlsafe_b64decode(pad_header))
    assert header == {"alg": "HS256", "typ": "JWT", "kid": DEV_JWT_KID}

    pad_claims = parts[1] + "=" * (-len(parts[1]) % 4)
    claims = json.loads(base64.urlsafe_b64decode(pad_claims))
    assert claims["iss"] == settings.JWT_ISSUER
    assert claims["aud"] == settings.JWT_AUDIENCE
    assert claims["sub"] == "merchant_one"
    assert claims["role"] == "customer"
    assert claims["key_id"] == "dev_key_id"
    assert claims["exp"] == 1_700_000_000 + settings.ACCESS_TOKEN_TTL_S
    assert isinstance(claims["jti"], str) and claims["jti"]

    decoded = decode_access_token(token, now=1_700_000_010)
    assert decoded == Principal(user_id="merchant_one", role="customer", key_id="dev_key_id")


def test_signing_key_rotation_two_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    principal = Principal(user_id="op_rot", role="operator", key_id="abcd1234ef56")

    monkeypatch.setattr(settings, "JWT_SIGNING_KEYS", f"kid1:{_SECRET_ALPHA}")
    monkeypatch.setattr(settings, "JWT_ACTIVE_KID", "kid1")
    tok_old, _ = issue_access_token(principal, now=1_700_000_000)

    monkeypatch.setattr(settings, "JWT_SIGNING_KEYS", f"kid1:{_SECRET_ALPHA};kid2:{_SECRET_BETA}")
    monkeypatch.setattr(settings, "JWT_ACTIVE_KID", "kid2")
    tok_new, _ = issue_access_token(principal, now=1_700_000_005)

    assert decode_access_token(tok_old, now=1_700_000_010) == principal
    assert decode_access_token(tok_new, now=1_700_000_010) == principal

    h_new = json.loads(base64.urlsafe_b64decode(tok_new.split(".")[0] + "=="))
    assert h_new["kid"] == "kid2"

    monkeypatch.setattr(settings, "JWT_SIGNING_KEYS", f"kid2:{_SECRET_BETA}")
    with pytest.raises(TokenError) as exc_old:
        decode_access_token(tok_old, now=1_700_000_010)
    assert exc_old.value.reason == "unknown_kid"
    assert decode_access_token(tok_new, now=1_700_000_010) == principal


def test_token_expiration_and_not_before_leeway(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ACCESS_TOKEN_TTL_S", 60)
    principal = Principal(user_id="merchant_two", role="customer", key_id="key_two")
    now = 1_700_000_000
    token, ttl = issue_access_token(principal, now=now)
    assert ttl == 60

    assert decode_access_token(token, now=now + 89) == principal
    assert decode_access_token(token, now=now - 30) == principal

    with pytest.raises(TokenError) as exc_exp:
        decode_access_token(token, now=now + 91)
    assert exc_exp.value.reason == "expired"

    with pytest.raises(TokenError) as exc_nbf:
        decode_access_token(token, now=now - 31)
    assert exc_nbf.value.reason == "not_yet_valid"


def test_tampered_signature_and_payload_rejected() -> None:
    principal = Principal(user_id="merchant_three", role="customer", key_id="key_three")
    token, _ = issue_access_token(principal, now=1_700_000_000)
    header_b64, claims_b64, sig_b64 = token.split(".")

    flipped = ("A" if sig_b64[0] != "A" else "B") + sig_b64[1:]
    with pytest.raises(TokenError) as exc_sig:
        decode_access_token(f"{header_b64}.{claims_b64}.{flipped}", now=1_700_000_005)
    assert exc_sig.value.reason == "bad_signature"

    elevated = _b64u(
        {
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "sub": "merchant_three",
            "role": "operator",
            "key_id": "key_three",
            "iat": 1_700_000_000,
            "nbf": 1_700_000_000,
            "exp": 1_700_000_900,
            "jti": "tampered",
        }
    )
    with pytest.raises(TokenError) as exc_claim:
        decode_access_token(f"{header_b64}.{elevated}.{sig_b64}", now=1_700_000_005)
    assert exc_claim.value.reason == "bad_signature"


def test_alg_none_and_unsupported_algorithm_rejected() -> None:
    claims = _b64u(
        {
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "sub": "merchant_x",
            "role": "customer",
            "key_id": "dev",
            "iat": 1_700_000_000,
            "nbf": 1_700_000_000,
            "exp": 1_700_000_900,
            "jti": "abc",
        }
    )
    for alg in ("none", "None", "HS512", "RS256"):
        header = _b64u({"alg": alg, "typ": "JWT", "kid": DEV_JWT_KID})
        with pytest.raises(TokenError) as exc_alg:
            decode_access_token(f"{header}.{claims}.AAAA", now=1_700_000_005)
        assert exc_alg.value.reason == "bad_algorithm"


def test_wrong_issuer_audience_and_role_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    orig_issuer = settings.JWT_ISSUER
    orig_audience = settings.JWT_AUDIENCE
    monkeypatch.setattr(settings, "JWT_SIGNING_KEYS", f"kid1:{_SECRET_ALPHA}")
    monkeypatch.setattr(settings, "JWT_ACTIVE_KID", "kid1")
    principal = Principal(user_id="merchant_four", role="customer", key_id="key_four")
    token, _ = issue_access_token(principal, now=1_700_000_000)

    monkeypatch.setattr(settings, "JWT_ISSUER", "other-issuer")
    with pytest.raises(TokenError) as exc_iss:
        decode_access_token(token, now=1_700_000_005)
    assert exc_iss.value.reason == "bad_issuer"

    monkeypatch.setattr(settings, "JWT_ISSUER", orig_issuer)
    monkeypatch.setattr(settings, "JWT_AUDIENCE", "other-audience")
    with pytest.raises(TokenError) as exc_aud:
        decode_access_token(token, now=1_700_000_005)
    assert exc_aud.value.reason == "bad_audience"

    monkeypatch.setattr(settings, "JWT_AUDIENCE", orig_audience)
    header_b64 = _b64u({"alg": "HS256", "typ": "JWT", "kid": "kid1"})
    claims_b64 = _b64u(
        {
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "sub": "merchant_four",
            "role": "superadmin",
            "key_id": "key_four",
            "iat": 1_700_000_000,
            "nbf": 1_700_000_000,
            "exp": 1_700_000_900,
            "jti": "badrole",
        }
    )
    import hashlib
    import hmac

    sig = base64.urlsafe_b64encode(
        hmac.new(_SECRET_ALPHA.encode("utf-8"), f"{header_b64}.{claims_b64}".encode("ascii"), hashlib.sha256).digest()
    ).rstrip(b"=").decode("ascii")
    with pytest.raises(TokenError) as exc_role:
        decode_access_token(f"{header_b64}.{claims_b64}.{sig}", now=1_700_000_005)
    assert exc_role.value.reason == "bad_role"


def test_malformed_tokens_rejected() -> None:
    bad_samples = [
        "",
        "   ",
        "only.two",
        "a.b.c.d",
        "not_base64!.abc.def",
        f"{_b64u(['not', 'dict'])}.{_b64u({'a': 1})}.abc",
    ]
    for sample in bad_samples:
        with pytest.raises(TokenError) as exc_mal:
            decode_access_token(sample, now=1_700_000_000)
        assert exc_mal.value.reason == "malformed"


def test_validate_signing_keys_production_enforcement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "JWT_SIGNING_KEYS", "")
    monkeypatch.setattr(settings, "JWT_ACTIVE_KID", "")
    with pytest.raises(ValueError, match="JWT_SIGNING_KEYS"):
        validate_signing_keys_config()

    monkeypatch.setattr(settings, "JWT_SIGNING_KEYS", "kid1:too-short-secret")
    monkeypatch.setattr(settings, "JWT_ACTIVE_KID", "kid1")
    with pytest.raises(ValueError, match="32"):
        validate_signing_keys_config()

    monkeypatch.setattr(settings, "JWT_SIGNING_KEYS", f"{DEV_JWT_KID}:{_SECRET_ALPHA}")
    monkeypatch.setattr(settings, "JWT_ACTIVE_KID", DEV_JWT_KID)
    with pytest.raises(ValueError, match="dev"):
        validate_signing_keys_config()

    monkeypatch.setattr(settings, "JWT_SIGNING_KEYS", f"kid1:{DEV_JWT_SECRET}")
    monkeypatch.setattr(settings, "JWT_ACTIVE_KID", "kid1")
    with pytest.raises(ValueError, match="development signing secret"):
        validate_signing_keys_config()

    monkeypatch.setattr(settings, "JWT_SIGNING_KEYS", f"kid1:{_SECRET_ALPHA}")
    monkeypatch.setattr(settings, "JWT_ACTIVE_KID", "missing")
    with pytest.raises(ValueError, match="JWT_ACTIVE_KID"):
        validate_signing_keys_config()

    monkeypatch.setattr(settings, "JWT_SIGNING_KEYS", f"kid1:{_SECRET_ALPHA};kid2:{_SECRET_BETA}")
    monkeypatch.setattr(settings, "JWT_ACTIVE_KID", "kid2")
    validate_signing_keys_config()

    valid_api_hash = hash_api_key("prod-merchant-secret-01")
    monkeypatch.setattr(settings, "API_KEYS", f"{valid_api_hash}:merchant_prod:customer:2099-12-31")
    validate_auth_config()


def test_parse_signing_keys_errors() -> None:
    assert parse_signing_keys("") == {}
    with pytest.raises(ValueError):
        parse_signing_keys("missing_colon")
    with pytest.raises(ValueError):
        parse_signing_keys("bad kid:" + _SECRET_ALPHA)
    with pytest.raises(ValueError):
        parse_signing_keys(f"dup:{_SECRET_ALPHA};dup:{_SECRET_BETA}")
    with pytest.raises(ValueError):
        parse_signing_keys("short:abc")


def test_parse_api_keys_expiry_and_is_principal_expired() -> None:
    digest_a = hash_api_key("secret-key-alpha")
    digest_b = hash_api_key("secret-key-beta")
    parsed = parse_api_keys(f"{digest_a}:merchant_a:customer:2026-12-31;{digest_b}:operator_b:operator")

    assert parsed[digest_a].not_after == "2026-12-31"
    assert parsed[digest_b].not_after is None
    assert "getnet-dev-key" in DEV_API_KEYS

    today = datetime(2026, 12, 31, tzinfo=UTC).date()
    assert not is_principal_expired(parsed[digest_a], today_utc=today)
    assert is_principal_expired(parsed[digest_a], today_utc=today + timedelta(days=1))
    assert not is_principal_expired(parsed[digest_b], today_utc=today + timedelta(days=100))

    with pytest.raises(ValueError):
        parse_api_keys(f"{digest_a}:merchant_a:customer:2026-02-30")
    with pytest.raises(ValueError, match="expiry"):
        parse_api_keys(f"{digest_a}:merchant_a:customer:not-a-date")
