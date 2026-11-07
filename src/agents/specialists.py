"""Specialist sub-agents (KnowledgeAgent, SupportAgent) with isolated execution contexts."""
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage

from src.config import settings
from src.core.llm import (
    get_chat_model,
    get_fallback_model,
    invoke_model_with_fallback,
)

logger = logging.getLogger("multiagent.specialists")


class SpecialistAgent:
    """Specialist sub-agent delegating to a dedicated model loop with isolated tools."""

    def __init__(
        self,
        name: str,
        prompt_file: str,
        tools: list[Any],
        chat_model: BaseChatModel | None = None,
        fallback_model: BaseChatModel | None = None,
    ):
        self.name = name
        self.prompt_file = prompt_file
        self.tools = list(tools)
        self.tools_by_name = {t.name: t for t in self.tools}
        self.prompt = self._load_prompt(prompt_file)
        self.chat_model = chat_model
        self.fallback_model = fallback_model
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
                    continue

                tool_fn = self.tools_by_name[tool_name]
                try:
                    result_str = tool_fn.invoke(
                        tool_args,
                        config={"configurable": {"user_id": user_id}},
                    )
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Error executing tool {tool_name} in {self.name}: {e}")
                    result_str = json.dumps({"error": f"tool {tool_name} failed: {e}"})

                tools_used.append(tool_name)
                t_msg = ToolMessage(content=result_str, tool_call_id=call_id, name=tool_name)
                messages.append(t_msg)

                try:
                    parsed = json.loads(result_str) if isinstance(result_str, str) else result_str
                    if isinstance(parsed, dict):
                        if tool_name == "search_knowledge_base":
                            docs = parsed.get("documents", [])
                            for d in docs:
                                retrieved_docs.append(d)
                                if d.get("url"):
                                    sources.append(d.get("url"))
                        elif tool_name == "search_web":
                            results = parsed.get("results", [])
                            for r in results:
                                if r.get("url"):
                                    sources.append(r.get("url"))
                except (json.JSONDecodeError, TypeError, KeyError):
                    pass

        return {
            "agent": self.name,
            "status": "step_limit",
            "answer": "",
            "tools_used": tools_used,
            "sources": sources,
            "retrieved_docs": retrieved_docs,
        }
