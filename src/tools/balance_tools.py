"""Customer Support tools for querying merchant sales, settlements, and declines."""
from typing import Any

from src.core.mock_db import get_mock_db
from src.core.pii import mask_bank_account


def get_settlement_and_sales_status(user_id: str) -> dict[str, Any]:
    """Retrieve settlement information for yesterday's sales and current balance."""
    db = get_mock_db()
    user = db.get_user(user_id)
    if not user:
        return {"error": f"Lojista '{user_id}' não encontrado."}

    settlement = user.get("settlements", {})
    yesterday = settlement.get("yesterday_sales", {})

    return {
        "status": "success",
        "user_id": user_id,
        "merchant_name": user.get("trade_name"),
        "yesterday_sales": {
            "date": yesterday.get("date"),
            "total_transactions": yesterday.get("total_transactions"),
            "gross_amount_brl": yesterday.get("gross_amount"),
            "discounts_fees_brl": yesterday.get("discounts_fees"),
            "net_amount_brl": yesterday.get("net_amount"),
            "settlement_date": yesterday.get("settlement_date"),
            "estimated_deposit_time": yesterday.get("estimated_deposit_time"),
            "status": yesterday.get("status"),
            "destination_account": mask_bank_account(yesterday.get("destination_account"))
        },
        "available_for_anticipation_brl": settlement.get("available_for_anticipation")
    }


def get_declined_transaction_details(user_id: str, error_code: str | None = None) -> dict[str, Any]:
    """Retrieve details of recent transaction declines and root-cause explanations."""
    db = get_mock_db()
    user = db.get_user(user_id)
    if not user:
        return {"error": f"Lojista '{user_id}' não encontrado."}

    recent_txns = user.get("recent_transactions", [])
    declined = [t for t in recent_txns if t.get("status") == "DECLINED"]
    latest_declined = declined[0] if declined else None

    code_to_check = error_code or (latest_declined.get("error_code") if latest_declined else None)

    if code_to_check is None:
        code_known = None
        code_details = None
    elif code_to_check in db.decline_code_catalog:
        code_known = True
        catalog_info = db.decline_code_catalog[code_to_check]
        code_details = {
            "error_code": code_to_check,
            "title": catalog_info.get("name"),
            "cause": catalog_info.get("description"),
            "recommended_action": catalog_info.get("solution"),
        }
    else:
        code_known = False
        code_details = None

    return {
        "status": "success",
        "user_id": user_id,
        "latest_declined_transaction": latest_declined,
        "queried_code": code_to_check,
        "code_known": code_known,
        "code_details": code_details,
    }
