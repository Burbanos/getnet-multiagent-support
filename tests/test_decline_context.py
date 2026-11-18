"""Offline tests for decline-catalogue code_context applicability (Phase 13B)."""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from src.tools.agent_tools import diagnose_declined_transaction


def test_terminal_screen_returns_not_applicable_without_catalogue_or_txn() -> None:
    cfg = {"configurable": {"user_id": "cliente1988"}}
    raw = diagnose_declined_transaction.invoke({"code_context": "terminal_screen", "error_code": "05"}, config=cfg)
    res = json.loads(raw)

    assert res == {
        "status": "not_applicable",
        "code_context": "terminal_screen",
        "queried_code": "05",
        "reason": "o catálogo cobre apenas códigos de recusa de transação de cartão; o código não veio de uma venda recusada",
    }
    assert "Emissor" not in raw
    assert "TXN-" not in raw


def test_app_context_returns_not_applicable_even_without_transaction_lookup() -> None:
    cfg = {"configurable": {"user_id": "lojista_inexistente"}}
    raw = diagnose_declined_transaction.invoke({"code_context": "app", "error_code": "51"}, config=cfg)
    res = json.loads(raw)

    assert res["status"] == "not_applicable"
    assert res["code_context"] == "app"
    assert res["queried_code"] == "51"
    assert "code_details" not in res
    assert "latest_declined_transaction" not in res


def test_declined_sale_returns_catalogue_meaning_and_transaction_data() -> None:
    cfg = {"configurable": {"user_id": "cliente1988"}}
    res = json.loads(
        diagnose_declined_transaction.invoke({"code_context": "declined_sale", "error_code": "05"}, config=cfg)
    )
    assert res["status"] == "success"
    assert res["code_details"]["title"] == "Não Autorizada / Contate o Emissor"
    assert res["latest_declined_transaction"]["transaction_id"] == "TXN-902188"


def test_unknown_context_preserves_current_behavior() -> None:
    cfg_ok = {"configurable": {"user_id": "cliente1988"}}
    res_ok = json.loads(diagnose_declined_transaction.invoke({"code_context": "unknown"}, config=cfg_ok))
    assert res_ok["status"] == "success"
    assert res_ok["code_details"]["title"] == "Saldo / Limite Insuficiente"

    cfg_missing = {"configurable": {"user_id": "nao_existe"}}
    res_missing = json.loads(
        diagnose_declined_transaction.invoke({"code_context": "unknown", "error_code": "51"}, config=cfg_missing)
    )
    assert res_missing == {"status": "not_found", "error": "merchant_not_found"}


def test_code_context_is_required_in_tool_schema() -> None:
    schema = diagnose_declined_transaction.tool_call_schema.model_json_schema()
    assert "code_context" in (schema.get("required") or [])

    cfg = {"configurable": {"user_id": "cliente1988"}}
    with pytest.raises(ValidationError):
        diagnose_declined_transaction.invoke({"error_code": "05"}, config=cfg)
