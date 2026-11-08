"""Token pricing calculation based on official Google AI pricing table."""
from __future__ import annotations

PRICE_SOURCE_URL = "https://ai.google.dev/gemini-api/docs/pricing"
PRICE_PAGE_LAST_UPDATED = "2026-10-30"
PRICE_RETRIEVED_AT = "2026-11-07"
PRICE_TIER = "paid tier, Standard, text input"

PRICES_USD_PER_1M: dict[str, dict[str, float]] = {
    "gemini-3.5-flash-lite": {"input": 0.30, "output": 2.50},
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
    "gemini-embedding-2": {"input": 0.20, "output": 0.0},
}


def cost_usd(
    model: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
) -> float | None:
    """
    Calculate estimated cost in USD based on input and output tokens.

    Strips 'models/' prefix from model name if present.
    Returns None if:
    - model is None or not in PRICES_USD_PER_1M
    - input_tokens is None or output_tokens is None
    Otherwise returns round(input_tokens / 1_000_000 * input + output_tokens / 1_000_000 * output, 8).
    """
    if model is None or input_tokens is None or output_tokens is None:
        return None

    clean_model = model.removeprefix("models/") if model.startswith("models/") else model
    if clean_model not in PRICES_USD_PER_1M:
        return None

    rates = PRICES_USD_PER_1M[clean_model]
    inp_rate = rates["input"]
    out_rate = rates["output"]

    total = (input_tokens / 1_000_000.0) * inp_rate + (output_tokens / 1_000_000.0) * out_rate
    return round(total, 8)
