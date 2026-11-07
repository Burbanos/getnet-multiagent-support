from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class ScriptedChatModel(BaseChatModel):
    """Deterministic chat model for tests: returns scripted AIMessages in order and records inputs."""
    responses: list[AIMessage] = Field(default_factory=list)
    received: list[list[BaseMessage]] = Field(default_factory=list)
    bound_tools: list[Any] = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        self.bound_tools = list(tools)
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        if not self.responses:
            raise RuntimeError("ScriptedChatModel: no scripted responses left")
        return ChatResult(generations=[ChatGeneration(message=self.responses.pop(0))])

    @property
    def _llm_type(self) -> str:
        return "scripted-fake"


class KeywordFakeEmbedder:
    """Deterministic keyword count fake embedder for testing."""

    def __init__(self, keywords: list[str]) -> None:
        self.keywords = keywords

    def _vec(self, text: str) -> list[float]:
        t = text.lower()
        return [float(t.count(k)) for k in self.keywords] + [0.01]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)
