"""Deterministic post-supervisor answer validation (URLs, ticket IDs, time promises)."""
from __future__ import annotations

from urllib.parse import unquote

from src.rag.lexical import fold

URL_TRAILING = ")]}>.,;:!?\"'*`"
TICKET_PREFIX = "GET-TKT-"
PROMISE_PHRASES = (
    "em breve",
    "em instantes",
    "logo mais",
    "em alguns minutos",
    "em poucos minutos",
    "em ate",
    "dentro de",
    "prazo de",
    "nas proximas",
    "shortly",
    "soon",
    "within",
    "in a few",
    "in the next",
    "as soon as",
)


def extract_urls(text: str) -> list[str]:
    """Extract unique HTTP(S) URLs preserving order, splitting markdown links and stripping trailing chars."""
    out: list[str] = []
    for tok in text.split():
        for pre in ("https://", "http://"):
            idx = tok.find(pre)
            if idx >= 0:
                for part in tok[idx:].split("]("):
                    if not part.startswith(("https://", "http://")):
                        continue
                    while part and part[-1] in URL_TRAILING:
                        part = part[:-1]
                    if len(part) > 8 and part not in out:
                        out.append(part)
                break
    return out


def extract_ticket_ids(text: str) -> list[str]:
    """Extract unique GET-TKT-... identifiers preserving order."""
    out: list[str] = []
    idx = text.find(TICKET_PREFIX)
    while idx >= 0:
        end = idx + len(TICKET_PREFIX)
        while end < len(text) and (text[end].isalnum() or text[end] == "-"):
            end += 1
        tid = text[idx:end].rstrip("-")
        if tid not in out:
            out.append(tid)
        idx = text.find(TICKET_PREFIX, end)
    return out


def find_promises(text: str) -> list[str]:
    """Find whole-phrase timing promises in folded normalized text preserving PROMISE_PHRASES order."""
    padded = " " + " ".join(fold(text).split()) + " "
    return [phrase for phrase in PROMISE_PHRASES if f" {phrase} " in padded]


def check_answer(
    answer: str,
    evidence: str,
    ticket_ids: set[str],
    ticket_turn: bool,
) -> dict[str, list[str]]:
    """Return only failed check categories in fixed order: urls, ticket_ids, time_promise."""
    ev_norm = unquote(evidence).lower()
    failed: dict[str, list[str]] = {}

    bad_urls = [u for u in extract_urls(answer) if unquote(u).lower().rstrip("/") not in ev_norm]
    if bad_urls:
        failed["urls"] = bad_urls

    bad_tickets = [tid for tid in extract_ticket_ids(answer) if tid not in ticket_ids and tid not in evidence]
    if bad_tickets:
        failed["ticket_ids"] = bad_tickets

    if ticket_turn:
        promises = find_promises(answer)
        if promises:
            failed["time_promise"] = promises

    return failed
