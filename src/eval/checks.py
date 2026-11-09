"""Deterministic verification checks for single evaluation cases."""
from typing import Any

PT_WORDS = {
    "de", "que", "não", "para", "com", "uma", "os", "seu", "sua", "você", "é", "está", "são",
    "pelo", "pela", "nas", "nos", "também", "mas", "ou", "quando", "como", "ao", "à", "em",
    "da", "dos", "das", "na", "um", "se", "por", "mais", "isso",
}
EN_WORDS = {
    "the", "and", "you", "your", "is", "are", "to", "of", "for", "with", "this", "that",
    "it", "can", "will", "be", "not", "have", "from", "on", "in", "or", "by", "at", "an",
    "we", "our", "please", "if", "what",
}
STRIP = ".,;:!?()[]{}\"'*`«»“”‘’-/"

CHECKS = (
    "routing_ok",
    "tools_ok",
    "escalation_ok",
    "priority_ok",
    "blocked_ok",
    "sources_ok",
    "facts_ok",
    "facts_none_ok",
    "language_ok",
)
SPECIALISTS = {"KnowledgeAgent", "SupportAgent"}


def norm(s: str) -> str:
    """Normalize string by collapsing whitespace and lowercasing."""
    return " ".join((s or "").split()).lower()


def detect_language(text: str) -> str:
    """
    Detect language (pt vs en) based on token frequency in predefined lexicons.
    Returns 'pt', 'en', or 'unknown' on tie or no matches.
    """
    pt = 0
    en = 0
    for w in (text or "").lower().split():
        w = w.strip(STRIP)
        pt += w in PT_WORDS
        en += w in EN_WORDS
    return "pt" if pt > en else "en" if en > pt else "unknown"


def evaluate_case(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluate a case result against ground truth expectations using deterministic checks.
    Evaluations run on the last turn of multi-turn conversations.
    """
    out: dict[str, Any] = {k: None for k in CHECKS}
    if result.get("status") != "ok" or not result.get("turns"):
        return {"checks": out, "passed": False}

    t = result["turns"][-1]
    e = case["expect"]
    spec = {a for a in t.get("agents_used", []) if a in SPECIALISTS}
    used = t.get("tools_used", [])
    resp = norm(t.get("response", ""))

    if e["agents"] is not None:
        out["routing_ok"] = spec == set(e["agents"])

    if e["tools_all"] or e["tools_none"]:
        tools_ok = all(x in used for x in e["tools_all"]) and not any(
            x in used for x in e["tools_none"]
        )
        if e.get("api_status"):
            for tool, st in e["api_status"].items():
                tools_ok = tools_ok and any(
                    a.get("tool") == tool and a.get("status") == st
                    for a in (t.get("api_results") or [])
                )
        out["tools_ok"] = tools_ok

    if e["escalate"] is not None:
        out["escalation_ok"] = (t.get("ticket_id") is not None) == e["escalate"]

    if e["priority"] is not None:
        out["priority_ok"] = t.get("ticket_priority") == e["priority"]

    out["blocked_ok"] = (not t.get("is_safe", True)) == e["blocked"]

    if e["gold_urls"]:
        out["sources_ok"] = any(u in t.get("sources", []) for u in e["gold_urls"])

    if e["facts_any"]:
        out["facts_ok"] = all(
            any(norm(a) in resp for a in grp) for grp in e["facts_any"]
        )

    if e["facts_none"]:
        out["facts_none_ok"] = not any(norm(x) in resp for x in e["facts_none"])

    if not e["blocked"] and t.get("is_safe", True) and not t.get("handoff"):
        out["language_ok"] = detect_language(t.get("response", "")) == case["lang"]

    return {"checks": out, "passed": all(v for v in out.values() if v is not None)}
