"""Tests for dedicated 'auth' scenario key isolation in scripts/compose_evidence.py."""
from __future__ import annotations

import scripts.compose_evidence as ce


def test_auth_checks_uses_only_auth_key_and_passes_all_four() -> None:
    keys, _ = ce.make_api_keys()
    seen_calls: list[tuple[str, str, str | None, str | None]] = []
    owners: dict[str, str | None] = {}
    spent_refresh: set[str] = set()
    revoked_families: set[str] = set()
    counter = 0

    def fake_http(method: str, url: str, *, api_key=None, bearer_token=None, body=None, timeout=45.0):
        nonlocal counter
        seen_calls.append((method, url, api_key, bearer_token))
        if url.endswith("/auth/token"):
            counter += 1
            acc = f"acc.{counter}.sig"
            ref = f"ref-{counter}"
            owners[acc] = api_key
            owners[ref] = api_key
            return 200, {}, {"access_token": acc, "refresh_token": ref}
        if url.endswith("/auth/refresh"):
            tok = (body or {}).get("refresh_token", "")
            family = tok.split("-")[1] if "-" in tok else tok
            if tok in spent_refresh:
                revoked_families.add(family)
                return 401, {}, {}
            if family in revoked_families or tok not in owners:
                return 401, {}, {}
            spent_refresh.add(tok)
            counter += 1
            acc = f"acc.{counter}.sig"
            ref = f"ref-{tok.split('-')[1]}-{counter}"
            owners[acc] = owners[tok]
            owners[ref] = owners[tok]
            return 200, {}, {"access_token": acc, "refresh_token": ref}
        if bearer_token in owners:
            return 200, {}, {"messages": []}
        return 401, {}, {}

    res = ce.auth_checks(keys, "run-unit", http=fake_http)

    assert {c[2] for c in seen_calls if c[2]} == {keys["auth"]}
    assert {owners.get(c[3]) for c in seen_calls if c[3] in owners} <= {keys["auth"]}
    assert res["checks"] == {
        "token_cross_replica": True,
        "tampered_token_rejected": True,
        "refresh_rotation_cross_replica": True,
        "refresh_reuse_revokes_family": True,
    }
    assert len(res["raw_refresh_tokens"]) == 4
    assert res["auth_tokens"]["tampered_status"] == 401


def test_auth_checks_detects_failed_tamper_or_reuse_checks() -> None:
    keys, _ = ce.make_api_keys()

    def permissive_http(method: str, url: str, *, api_key=None, bearer_token=None, body=None, timeout=45.0):
        if url.endswith("/auth/token"):
            return 200, {}, {"access_token": "a.b.c", "refresh_token": "r-1"}
        if url.endswith("/auth/refresh"):
            return 200, {}, {"access_token": "a2.b.c", "refresh_token": "r-2"}
        return 200, {}, {}

    res = ce.auth_checks(keys, "run-fail", http=permissive_http)
    assert res["checks"]["token_cross_replica"] is True
    assert res["checks"]["tampered_token_rejected"] is False
    assert res["checks"]["refresh_reuse_revokes_family"] is False
