"""Tests verifying that mock database and account tools never invent a merchant (Phase 9D)."""
from __future__ import annotations

import json

from src.core.mock_db import MockDatabase
from src.tools.agent_tools import (
    diagnose_declined_transaction,
    diagnose_terminal,
    get_settlement_status,
)
from src.tools.balance_tools import (
    get_declined_transaction_details,
    get_settlement_and_sales_status,
)
from src.tools.terminal_tools import diagnose_terminal_connectivity

NOT_FOUND = {"status": "not_found", "error": "merchant_not_found"}
UNKNOWN_USER = "lojista_que_nao_existe"


def test_unknown_merchant_has_no_record():
    """MockDatabase returns None for an unknown merchant and returns a dict for cliente1988."""
    db = MockDatabase()
    assert db.get_user(UNKNOWN_USER) is None
    known = db.get_user("cliente1988")
    assert isinstance(known, dict)
    assert known.get("user_id") == "cliente1988"


def test_settlement_unknown_merchant():
    """get_settlement_and_sales_status returns not_found for an unknown merchant."""
    res = get_settlement_and_sales_status(UNKNOWN_USER)
    assert res == NOT_FOUND


def test_declined_unknown_merchant():
    """get_declined_transaction_details returns not_found with or without error_code."""
    assert get_declined_transaction_details(UNKNOWN_USER) == NOT_FOUND
    assert get_declined_transaction_details(UNKNOWN_USER, error_code="51") == NOT_FOUND


def test_terminal_unknown_merchant():
    """diagnose_terminal_connectivity returns not_found with or without terminal_serial."""
    assert diagnose_terminal_connectivity(UNKNOWN_USER) == NOT_FOUND
    assert diagnose_terminal_connectivity(UNKNOWN_USER, terminal_serial="GET-883921") == NOT_FOUND


def test_agent_tool_returns_not_found():
    """Agent tool invocations return not_found as serialized JSON for unknown merchant."""
    cfg = {"configurable": {"user_id": UNKNOWN_USER}}

    res_settlement = json.loads(get_settlement_status.invoke({}, config=cfg))
    assert res_settlement == NOT_FOUND

    res_declined = json.loads(diagnose_declined_transaction.invoke({"error_code": "51"}, config=cfg))
    assert res_declined == NOT_FOUND

    res_terminal = json.loads(diagnose_terminal.invoke({}, config=cfg))
    assert res_terminal == NOT_FOUND


def test_known_merchant_unchanged():
    """Known merchant cliente1988 returns expected real data."""
    s = get_settlement_and_sales_status("cliente1988")
    assert s.get("status") == "success"
    assert s["yesterday_sales"]["net_amount_brl"] == 3367.2

    d = get_declined_transaction_details("cliente1988", error_code="51")
    assert d.get("status") == "success"
    assert d.get("code_known") is True

    t = diagnose_terminal_connectivity("cliente1988")
    assert t.get("status") == "success"
    assert t.get("serial_number") == "GET-883921"
