"""Evaluation dataset loading, validation, and checksum calculation."""
import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_CASE_KEYS = {"id", "category", "lang", "official", "offline", "turns", "expect"}
REQUIRED_EXPECT_KEYS = {
    "agents",
    "tools_all",
    "tools_none",
    "escalate",
    "priority",
    "blocked",
    "gold_urls",
    "facts_any",
    "facts_none",
    "abstain",
}
VALID_CATEGORIES = {
    "knowledge",
    "support",
    "web",
    "uncovered",
    "off_topic",
    "safety",
    "pii",
    "escalation",
    "multi_turn",
    "multi_intent",
    "public_data",
}
VALID_LANGS = {"pt", "en"}
VALID_AGENTS = {"KnowledgeAgent", "SupportAgent"}
VALID_TOOLS = {
    "search_knowledge_base",
    "get_weather_forecast",
    "get_exchange_rate",
    "search_web",
    "get_settlement_status",
    "diagnose_declined_transaction",
    "diagnose_terminal",
    "escalate_to_human",
}
API_TOOLS = {"get_weather_forecast", "get_exchange_rate"}
API_STATUSES = {"success", "not_found", "no_data", "unavailable", "invalid_request"}
OPTIONAL_EXPECT_KEYS = {"api_status"}


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    """
    Load and validate evaluation cases from a JSONL file.

    Raises ValueError if schema or semantic constraints are violated.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Cases file not found: {p}")

    content = p.read_text(encoding="utf-8")
    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for line_idx, line in enumerate(content.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Line {line_idx}: invalid JSON - {exc}") from exc

        if not isinstance(case, dict):
            raise ValueError(f"Line {line_idx}: case must be a JSON object")  # noqa: TRY004

        if set(case.keys()) != REQUIRED_CASE_KEYS:
            raise ValueError(
                f"Line {line_idx}: case keys {set(case.keys())} do not match {REQUIRED_CASE_KEYS}"
            )

        cid = case["id"]
        if not isinstance(cid, str) or not cid:
            raise ValueError(f"Line {line_idx}: invalid case id")
        if cid in seen_ids:
            raise ValueError(f"Line {line_idx}: duplicate case id '{cid}'")
        seen_ids.add(cid)

        if case["category"] not in VALID_CATEGORIES:
            raise ValueError(
                f"Line {line_idx}: invalid category '{case['category']}', expected one of {VALID_CATEGORIES}"
            )

        if case["lang"] not in VALID_LANGS:
            raise ValueError(
                f"Line {line_idx}: invalid lang '{case['lang']}', expected one of {VALID_LANGS}"
            )

        turns = case["turns"]
        if not isinstance(turns, list) or len(turns) == 0:
            raise ValueError(f"Line {line_idx}: turns must be a non-empty list")
        for t_idx, turn in enumerate(turns):
            if not isinstance(turn, str) or not turn.strip():
                raise ValueError(f"Line {line_idx}: turn {t_idx} must be a non-empty string")

        expect = case["expect"]
        if not isinstance(expect, dict):
            raise ValueError(f"Line {line_idx}: expect must be a JSON object")  # noqa: TRY004

        expect_keys = set(expect.keys())
        if not REQUIRED_EXPECT_KEYS.issubset(expect_keys) or not expect_keys.issubset(
            REQUIRED_EXPECT_KEYS | OPTIONAL_EXPECT_KEYS
        ):
            raise ValueError(
                f"Line {line_idx}: expect keys do not match {REQUIRED_EXPECT_KEYS}"
            )

        agents = expect["agents"]
        if agents is not None and (
            not isinstance(agents, list) or not all(a in VALID_AGENTS for a in agents)
        ):
            raise ValueError(
                f"Line {line_idx}: expect.agents must be None or list of valid agents {VALID_AGENTS}"
            )

        tools_all = expect["tools_all"]
        if not isinstance(tools_all, list) or not all(t in VALID_TOOLS for t in tools_all):
            raise ValueError(
                f"Line {line_idx}: expect.tools_all must be list of valid tools {VALID_TOOLS}"
            )

        tools_none = expect["tools_none"]
        if not isinstance(tools_none, list) or not all(t in VALID_TOOLS for t in tools_none):
            raise ValueError(
                f"Line {line_idx}: expect.tools_none must be list of valid tools {VALID_TOOLS}"
            )

        if "api_status" in expect:
            api_status = expect["api_status"]
            if not isinstance(api_status, dict) or len(api_status) == 0:
                raise ValueError(f"Line {line_idx}: expect.api_status must be a non-empty dict")
            for tool_k, status_v in api_status.items():
                if tool_k not in API_TOOLS:
                    raise ValueError(
                        f"Line {line_idx}: expect.api_status key '{tool_k}' must be one of {API_TOOLS}"
                    )
                if tool_k not in tools_all:
                    raise ValueError(
                        f"Line {line_idx}: expect.api_status key '{tool_k}' must be in expect.tools_all"
                    )
                if status_v not in API_STATUSES:
                    raise ValueError(
                        f"Line {line_idx}: expect.api_status value '{status_v}' must be one of {API_STATUSES}"
                    )

        if case.get("offline") and case.get("category") != "safety":
            raise ValueError(
                f"Line {line_idx}: offline is only permitted for category 'safety', got '{case['category']}'"
            )

        cases.append(case)

    return cases


def cases_sha256(cases: list[dict[str, Any]]) -> str:
    """Compute deterministic SHA256 checksum over the serialized list of cases."""
    serialized = "\n".join(
        json.dumps(c, ensure_ascii=False, sort_keys=True) for c in cases
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
