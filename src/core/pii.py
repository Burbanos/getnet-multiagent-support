"""PII Sanitization utilities for masking sensitive data (credit cards, CPFs)."""
import re
from typing import Tuple


def luhn_checksum(card_number: str) -> bool:
    """Validate credit card number using Luhn algorithm."""
    digits = [int(d) for d in card_number if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = d * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


def mask_card_number(match: re.Match) -> str:
    """Mask a credit card PAN, leaving only the last 4 digits visible."""
    raw = match.group(0)
    digits = re.sub(r"\D", "", raw)
    if len(digits) >= 13 and len(digits) <= 19 and luhn_checksum(digits):
        last4 = digits[-4:]
        return f"[CARTAO_MASCARADO_****{last4}]"
    return raw


def mask_cpf(match: re.Match) -> str:
    """Mask a Brazilian CPF, keeping only the final digits."""
    raw = match.group(0)
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11:
        # Simple exclusion for sequences like 00000000000
        if len(set(digits)) == 1:
            return raw
        last2 = digits[-2:]
        return f"[CPF_MASCARADO_***.***.***-{last2}]"
    return raw


# Patterns
CARD_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")
FORMATTED_CPF_PATTERN = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
UNFORMATTED_CPF_PATTERN = re.compile(r"\b\d{11}\b")


def sanitize_pii(text: str) -> Tuple[str, bool]:
    """
    Sanitize sensitive Personally Identifiable Information (PII) from text.
    
    Returns:
        Tuple containing sanitized string and boolean indicating if PII was detected.
    """
    if not text:
        return text, False

    original = text
    # 1. Mask credit cards
    masked = CARD_PATTERN.sub(mask_card_number, text)
    # 2. Mask formatted CPFs
    masked = FORMATTED_CPF_PATTERN.sub(mask_cpf, masked)
    # 3. Mask unformatted CPFs (only if not already masked as card)
    masked = UNFORMATTED_CPF_PATTERN.sub(mask_cpf, masked)

    pii_detected = masked != original
    return masked, pii_detected
