"""LLM-as-a-judge evaluation of groundedness, relevance, and abstention."""
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import settings
from src.core.llm import extract_model_name, get_chat_model

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "judge.md"


def _prompt_sha256(prompt_text: str) -> str:
    return hashlib.sha256(prompt_text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def load_judge_prompt(path: str | Path | None = None) -> str:
    """Read judge prompt from path (or default src/prompts/judge.md) with CRLF normalized to LF."""
    target = Path(path) if path is not None else PROMPT_PATH
    if not target.exists():
        raise FileNotFoundError(f"Judge prompt not found: {target}")
    return target.read_bytes().decode("utf-8").replace("\r\n", "\n")


def get_judge_model(model_name: str | None = None) -> Any:
    """Build and return chat model instance configured for the judge."""
    return get_chat_model(model_name or settings.EVAL_JUDGE_MODEL)


def response_text(message: Any) -> str:
    """
    Extract clean text content from a LangChain message or raw content.
    Concatenates text blocks, ignoring non-text blocks (e.g. thinking, image_url).
    """
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                itype = item.get("type")
                if itype in ("text", None) and "text" in item and isinstance(item["text"], str):
                    parts.append(item["text"])
        if parts:
            return "".join(parts)
        return ""
    return str(content or "")


def _extract_code_from_attr(obj: Any) -> int | None:
    for attr in ("code", "status_code"):
        val = getattr(obj, attr, None)
        if isinstance(val, int) and 100 <= val <= 599:
            return val
    return None


def error_code(exc: Exception) -> int | None:
    """
    Extract HTTP/gRPC status code from exception, cause chain, or message prefix.
    Returns integer between 100 and 599, or None.
    """
    curr: Any = exc
    while curr is not None:
        code = _extract_code_from_attr(curr)
        if code is not None:
            return code
        curr = getattr(curr, "__cause__", None)

    msg = str(exc).strip()
    if msg:
        first_word = msg.split()[0]
        if len(first_word) == 3 and first_word.isdigit():
            val = int(first_word)
            if 100 <= val <= 599:
                return val

    return None


_cached_chunk_texts: dict[str, str] | None = None


def load_chunk_texts(path: str | Path | None = None) -> dict[str, str]:
    """
    Load mapping from chunk_id to full text from index chunks.jsonl.
    Caches only the result of the default path.
    """
    global _cached_chunk_texts
    if path is None:
        if _cached_chunk_texts is not None:
            return _cached_chunk_texts
        target_path = Path(settings.INDEX_DIR) / "chunks.jsonl"
    else:
        target_path = Path(path)

    p = Path(target_path)
    if not p.exists():
        return {}

    mapping: dict[str, str] = {}
    content = p.read_text(encoding="utf-8")
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            cid = row.get("chunk_id")
            txt = row.get("text")
            if cid and txt is not None:
                mapping[cid] = str(txt)
        except json.JSONDecodeError:
            continue

    if path is None:
        _cached_chunk_texts = mapping
    return mapping


def build_judge_input(case: dict[str, Any], result: dict[str, Any]) -> str:
    """
    Format case conversation and final turn evidence as JSON for the judge.
    Never exposes ground truth expectations, case id, or category to avoid bias.
    """
    turns = result.get("turns", [])
    last_turn = turns[-1] if turns else {}

    raw_docs = last_turn.get("retrieved_docs", []) or []
    chunk_texts = load_chunk_texts()
    passages: list[dict[str, Any]] = []
    for d in raw_docs:
        if isinstance(d, dict):
            cid = d.get("chunk_id")
            full_text = chunk_texts.get(cid) if cid else None
            passages.append({
                "url": d.get("url", ""),
                "text": full_text if full_text is not None else str(d.get("text", "") or ""),
            })

    raw_web = last_turn.get("web_results", []) or []
    for w in raw_web:
        if isinstance(w, dict):
            url = w.get("url", "")
            title = w.get("title", "")
            snippet = w.get("snippet", "")
            passages.append({
                "url": url,
                "text": f"{title}\n{snippet}",
            })

    raw_api = last_turn.get("api_results", []) or []
    for a in raw_api:
        if isinstance(a, dict):
            passages.append({
                "url": a.get("source_url") or "",
                "text": json.dumps(a, ensure_ascii=False, sort_keys=True),
            })

    tool_outputs = last_turn.get("tool_results", []) or []

    payload = {
        "user_messages": case.get("turns", []),
        "final_response": last_turn.get("response", ""),
        "passages": passages,
        "tool_outputs": tool_outputs,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def parse_judgment(text: str) -> dict[str, Any]:
    """
    Parse and validate structured JSON judgment from raw model output.
    Extracts substring between first '{' and last '}'.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in judge output")

    snippet = text[start : end + 1]
    try:
        data = json.loads(snippet)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Judge output is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Judge output must be a JSON object")  # noqa: TRY004

    grounded = data.get("grounded")
    answers_question = data.get("answers_question")
    abstained = data.get("abstained")

    # Strictly reject booleans masquerading as integers
    if type(grounded) is not int or not (1 <= grounded <= 5):
        raise ValueError(f"Invalid 'grounded' value: {grounded}")

    if type(answers_question) is not int or not (1 <= answers_question <= 5):
        raise ValueError(f"Invalid 'answers_question' value: {answers_question}")

    if not isinstance(abstained, bool):
        raise ValueError(f"Invalid 'abstained' value: {abstained}")  # noqa: TRY004

    out: dict[str, Any] = {
        "grounded": grounded,
        "answers_question": answers_question,
        "abstained": abstained,
        "rationale": str(data.get("rationale") or ""),
    }
    if "acceptable" in data:
        acc = data.get("acceptable")
        if not isinstance(acc, bool):
            raise ValueError(f"Invalid 'acceptable' value: {acc}")
        out["acceptable"] = acc
    return out


def judge_case(
    case: dict[str, Any],
    result: dict[str, Any],
    model: Any,
    prompt_path: str | Path | None = None,
    prompt_text: str | None = None,
    prompt_sha: str | None = None,
    judge_model_name: str | None = None,
) -> dict[str, Any]:
    """
    Evaluate a single case result using the judge model.
    Returns status: ok with ratings (and acceptable when present) or status: error.
    Never leaks exception messages into judgment dictionary.
    """
    cid = case["id"]
    system_prompt = prompt_text if prompt_text is not None else load_judge_prompt(prompt_path)
    sha = prompt_sha if prompt_sha is not None else _prompt_sha256(system_prompt)
    user_content = build_judge_input(case, result)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    try:
        response = model.invoke(messages)
        text = response_text(response)
    except Exception as exc:  # noqa: BLE001
        return {
            "id": cid,
            "status": "error",
            "error_type": type(exc).__name__,
            "error_code": error_code(exc),
        }

    try:
        parsed = parse_judgment(text)
    except ValueError:
        return {
            "id": cid,
            "status": "error",
            "error_type": "unparseable",
            "error_code": None,
        }

    model_name = judge_model_name or extract_model_name(model)
    record: dict[str, Any] = {
        "id": cid,
        "status": "ok",
        "judge_model": model_name,
        "prompt_sha256": sha,
        "grounded": parsed["grounded"],
        "answers_question": parsed["answers_question"],
        "abstained": parsed["abstained"],
        "rationale": parsed["rationale"],
    }
    if "acceptable" in parsed:
        record["acceptable"] = parsed["acceptable"]
    return record


def should_judge(case: dict[str, Any], result: dict[str, Any]) -> bool:
    """
    Determine whether a case result qualifies for judge evaluation.
    Only evaluates ok, safe, non-handoff, and non-safety category turns.
    """
    if result.get("status") != "ok":
        return False
    if case.get("category") == "safety":
        return False

    turns = result.get("turns", [])
    if not turns:
        return False

    last = turns[-1]
    if not last.get("is_safe", True):
        return False
    return not bool(last.get("handoff"))


def load_judgments(path: str | Path) -> dict[str, dict[str, Any]]:
    """
    Load judgments from JSONL file into a dict indexed by case ID.
    If multiple lines exist for the same ID, the last one wins.
    """
    p = Path(path)
    if not p.exists():
        return {}

    judgments: dict[str, dict[str, Any]] = {}
    content = p.read_text(encoding="utf-8")
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            cid = row.get("id")
            if cid:
                judgments[cid] = row
        except json.JSONDecodeError:
            continue
    return judgments


def run_judge(
    cases: list[dict[str, Any]],
    results_path: str | Path,
    judgments_path: str | Path,
    model: Any | None = None,
    sleep_s: float | None = None,
    max_consecutive_errors: int = 3,
    prompt_path: str | Path | None = None,
    judge_model_name: str | None = None,
) -> dict[str, Any]:
    """
    Execute judge evaluation over eligible case results with resumption, mismatch guards, and error handling.
    """
    jp = Path(judgments_path)

    from src.eval.runner import load_results

    active_prompt_text = load_judge_prompt(prompt_path)
    active_prompt_sha = _prompt_sha256(active_prompt_text)

    delay = sleep_s if sleep_s is not None else settings.EVAL_SLEEP_S
    if model is not None:
        judge_model = model
    elif judge_model_name is not None:
        judge_model = get_judge_model(judge_model_name)
    else:
        judge_model = get_judge_model()
    active_model_name = judge_model_name or extract_model_name(judge_model)

    existing_judgments = load_judgments(jp)
    if jp.exists():
        for raw_ln in jp.read_text(encoding="utf-8").splitlines():
            raw_ln = raw_ln.strip()
            if not raw_ln:
                continue
            try:
                row = json.loads(raw_ln)
            except json.JSONDecodeError:
                continue
            if row.get("status") != "ok":
                continue
            old_model = row.get("judge_model")
            old_sha = row.get("prompt_sha256")
            if old_model is not None and old_model != active_model_name:
                raise ValueError(
                    f"Cannot resume judgments at {jp}: existing ok record uses judge_model={old_model!r}, "
                    f"expected {active_model_name!r}"
                )
            if old_sha is not None and old_sha != active_prompt_sha:
                raise ValueError(
                    f"Cannot resume judgments at {jp}: existing ok record uses prompt_sha256={old_sha!r}, "
                    f"expected {active_prompt_sha!r}"
                )

    jp.parent.mkdir(parents=True, exist_ok=True)
    results_by_id = load_results(results_path)

    attempted = 0
    ok = 0
    errors = 0
    skipped = 0
    stopped_early = False
    consecutive_errors = 0

    with open(jp, "a", encoding="utf-8") as f:
        for case in cases:
            cid = case["id"]
            res = results_by_id.get(cid)
            if not res or not should_judge(case, res):
                continue

            if existing_judgments.get(cid, {}).get("status") == "ok":
                skipped += 1
                continue

            j = judge_case(
                case,
                res,
                judge_model,
                prompt_text=active_prompt_text,
                prompt_sha=active_prompt_sha,
                judge_model_name=active_model_name,
            )
            f.write(json.dumps(j, ensure_ascii=False) + "\n")
            f.flush()

            attempted += 1
            if j.get("status") == "ok":
                ok += 1
                consecutive_errors = 0
            else:
                errors += 1
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    stopped_early = True
                    break

            if delay and delay > 0:
                time.sleep(delay)

    return {
        "attempted": attempted,
        "ok": ok,
        "errors": errors,
        "skipped": skipped,
        "stopped_early": stopped_early,
    }
