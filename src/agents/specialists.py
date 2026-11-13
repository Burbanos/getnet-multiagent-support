"""Specialist sub-agents (KnowledgeAgent, SupportAgent) with isolated execution contexts."""
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage

from src.config import settings
from src.core import metrics
from src.core.llm import (
    get_chat_model,
    get_fallback_model,
    invoke_model_with_fallback,
)

logger = logging.getLogger("multiagent.specialists")

API_TOOLS = frozenset({"get_weather_forecast", "get_exchange_rate"})


def _accumulate_usage(current: dict[str, int] | None, usage: dict[str, Any] | None) -> dict[str, int] | None:
    """Add token counts from usage into an existing accumulator dict, initializing on first non-empty usage."""
    if not isinstance(usage, dict):
        return current
    inp = int(usage.get("input_tokens") or 0)
    out = int(usage.get("output_tokens") or 0)
    tot = int(usage.get("total_tokens") or (inp + out))
    out_dict = dict(current) if current is not None else {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    out_dict["input_tokens"] += inp
    out_dict["output_tokens"] += out
    out_dict["total_tokens"] += tot
    return out_dict


class SpecialistAgent:
    """Specialist sub-agent delegating to a dedicated model loop with isolated tools."""

    def __init__(
        self,
        name: str,
        prompt_file: str,
        tools: list[Any],
        chat_model: BaseChatModel | None = None,
        fallback_model: BaseChatModel | None = None,
        web_classifier: Any | None = None,
    ):
        self.name = name
        self.prompt_file = prompt_file
        self.tools = list(tools)
        self.tools_by_name = {t.name: t for t in self.tools}
        self.prompt = self._load_prompt(prompt_file)
        self.chat_model = chat_model
        self.fallback_model = fallback_model
        self.web_classifier = web_classifier
        self._bound_model: Any = None
        self._bound_fallback: Any = None

    def _load_prompt(self, filename: str) -> str:
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return f"You are the {self.name}."

    def _get_bound_models(self) -> tuple[Any, Any]:
        if self._bound_model is None:
            if self.chat_model is not None:
                primary = self.chat_model
                fallback = self.fallback_model
            else:
                primary = get_chat_model()
                fallback = get_fallback_model()
            self._bound_model = primary.bind_tools(self.tools)
            self._bound_fallback = fallback.bind_tools(self.tools) if fallback is not None else None
        return self._bound_model, self._bound_fallback

    def run(self, task: str, user_id: str, trace_id: str) -> dict[str, Any]:
        """
        Execute the specialist loop in an isolated context.
        Messages: [SystemMessage(prompt.strip()), HumanMessage(task)].
        Runs model -> tools -> model loop up to settings.MAX_SPECIALIST_STEPS calls.
        """
        bound_model, bound_fallback = self._get_bound_models()
        messages: list[BaseMessage] = [
            SystemMessage(content=self.prompt.strip()),
            HumanMessage(content=task),
        ]

        tools_used: list[str] = []
        sources: list[str] = []
        retrieved_docs: list[dict[str, Any]] = []
        web_results: list[dict[str, Any]] = []
        api_results: list[dict[str, Any]] = []
        web_guardrail: list[dict[str, Any]] = []
        specialist_usage: dict[str, int] | None = None

        steps = 0
        max_steps = settings.MAX_SPECIALIST_STEPS

        while steps < max_steps:
            steps += 1
            ai_message, _ = invoke_model_with_fallback(
                bound_model,
                bound_fallback,
                messages,
                trace_id=trace_id,
                caller_name=self.name,
            )
            messages.append(ai_message)

            specialist_usage = _accumulate_usage(
                specialist_usage, getattr(ai_message, "usage_metadata", None)
            )

            tool_calls = getattr(ai_message, "tool_calls", None) or []
            if not tool_calls:
                answer = str(ai_message.text) if hasattr(ai_message, "text") else (
                    ai_message.content if isinstance(ai_message.content, str) else str(ai_message.content)
                )
                return {
                    "agent": self.name,
                    "status": "ok",
                    "answer": answer,
                    "tools_used": tools_used,
                    "sources": sources,
                    "retrieved_docs": retrieved_docs,
                    "web_results": web_results,
                    "api_results": api_results,
                    "web_guardrail": web_guardrail,
                    "usage": specialist_usage,
                }

            if steps >= max_steps:
                break

            for call in tool_calls:
                tool_name = call.get("name")
                tool_args = call.get("args", {})
                call_id = call.get("id", str(uuid.uuid4()))

                if tool_name not in self.tools_by_name:
                    err_msg = json.dumps({"error": f"tool {tool_name} not available to {self.name}"})
                    t_msg = ToolMessage(content=err_msg, tool_call_id=call_id, name=tool_name)
                    messages.append(t_msg)
                    metrics.inc_tool(tool_name, "error")
                    logger.info(
                        "tool finished",
                        extra={
                            "tool": tool_name,
                            "agent": self.name,
                            "status": "error",
                            "latency_ms": 0.0,
                        },
                    )
                    continue

                tool_fn = self.tools_by_name[tool_name]
                t0 = time.perf_counter()
                status = "ok"
                try:
                    result_str = tool_fn.invoke(
                        tool_args,
                        config={"configurable": {"user_id": user_id}},
                    )
                except Exception as e:  # noqa: BLE001
                    status = "error"
                    logger.error(f"Error executing tool {tool_name} in {self.name}: {type(e).__name__}")
                    result_str = json.dumps({"error": f"tool {tool_name} failed: {type(e).__name__}"})

                latency_ms = round((time.perf_counter() - t0) * 1000, 2)

                if (
                    tool_name == "search_web"
                    and self.web_classifier is not None
                    and settings.GUARDRAIL_WEB_RESULTS_ENABLED
                ):
                    try:
                        parsed_web = json.loads(result_str) if isinstance(result_str, str) else result_str
                    except (json.JSONDecodeError, TypeError):
                        parsed_web = None
                    if isinstance(parsed_web, dict) and parsed_web.get("status") == "success":
                        raw_results = parsed_web.get("results") or []
                        if raw_results:
                            screen_lines: list[str] = []
                            for idx, item in enumerate(raw_results, start=1):
                                if isinstance(item, dict):
                                    title = item.get("title") or ""
                                    snippet = item.get("snippet") or ""
                                    url = item.get("url") or ""
                                else:
                                    title, snippet, url = "", str(item), ""
                                screen_lines.append(f"[{idx}] {title}\n{snippet}\n{url}")
                            clf_res = self.web_classifier.classify("\n\n".join(screen_lines))
                            specialist_usage = _accumulate_usage(specialist_usage, clf_res.usage)
                            allowed = clf_res.status == "ok" and clf_res.verdict == "allow"
                            dropped = not allowed
                            if allowed:
                                metrics.inc_guardrail("web_allow")
                            else:
                                metrics.inc_guardrail(
                                    "web_unavailable" if clf_res.status == "error" else "web_block"
                                )
                                result_str = json.dumps(
                                    {
                                        "status": "blocked",
                                        "error": "web_results_blocked",
                                        "results": [],
                                    },
                                    ensure_ascii=False,
                                )
                            web_guardrail.append({
                                **clf_res.as_metadata(),
                                "results": len(raw_results),
                                "dropped": dropped,
                            })
                            logger.info(
                                "web results screened",
                                extra={"status": clf_res.status, "dropped": dropped},
                            )

                tools_used.append(tool_name)
                t_msg = ToolMessage(content=result_str, tool_call_id=call_id, name=tool_name)
                messages.append(t_msg)

                try:
                    parsed = json.loads(result_str) if isinstance(result_str, str) else result_str
                    if isinstance(parsed, dict):
                        if parsed.get("status") == "error" or "error" in parsed:
                            status = "error"
                        if tool_name == "search_knowledge_base":
                            docs = parsed.get("documents", [])
                            for d in docs:
                                retrieved_docs.append(d)
                                if d.get("url"):
                                    sources.append(d.get("url"))
                            retrieval_info = parsed.get("retrieval")
                            rerank_usage = (
                                retrieval_info.get("usage")
                                if isinstance(retrieval_info, dict)
                                else None
                            )
                            specialist_usage = _accumulate_usage(specialist_usage, rerank_usage)
                        elif tool_name == "search_web":
                            results = parsed.get("results", [])
                            for r in results:
                                if r.get("url"):
                                    sources.append(r.get("url"))
                                web_results.append({
                                    "url": r.get("url", ""),
                                    "title": r.get("title", ""),
                                    "snippet": r.get("snippet", ""),
                                })
                        elif tool_name in API_TOOLS:
                            api_results.append({"tool": tool_name, **parsed})
                            if parsed.get("status") == "success" and parsed.get("source_url"):
                                sources.append(parsed["source_url"])
                except (json.JSONDecodeError, TypeError, KeyError):
                    pass

                metrics.inc_tool(tool_name, status)
                logger.info(
                    "tool finished",
                    extra={
                        "tool": tool_name,
                        "agent": self.name,
                        "status": status,
                        "latency_ms": latency_ms,
                    },
                )

        return {
            "agent": self.name,
            "status": "step_limit",
            "answer": "",
            "tools_used": tools_used,
            "sources": sources,
            "retrieved_docs": retrieved_docs,
            "web_results": web_results,
            "api_results": api_results,
            "web_guardrail": web_guardrail,
            "usage": specialist_usage,
        }
