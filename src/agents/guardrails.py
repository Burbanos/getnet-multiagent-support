"""Input sanitization, PII masking, and prompt injection protection."""
import logging
import re
from typing import ClassVar

from src.config import settings
from src.core.pii import sanitize_pii
from src.core.state import AgentRole, AgentState

logger = logging.getLogger("multiagent.guardrails")


class GuardrailAgent:
    """Detects unsafe prompts, prompt injections, and masks sensitive PII (PAN/CPF)."""

    INJECTION_PATTERNS: ClassVar[list[str]] = [
        # English patterns
        r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
        r"your\s+system\s*prompt",
        r"you\s+are\s+now\s+dan",
        r"jailbreak",
        r"bypass\s+restrictions",
        r"exfiltrate",
        r"reveal\s+your\s+(secret|instructions|key)",
        # Portuguese patterns
        r"ignore\s+(todas\s+as\s+)?(suas\s+)?instru[cç][oõ]es",
        r"(me\s+)?mostre\s+(o\s+)?(seu\s+)?prompt",
        r"(suas|tuas)\s+regras\s+internas",
        r"(seu|teu)\s+prompt\s+de\s+sistema",
        r"esque[cç]a\s+(tudo\s+)?o\s+que\s+foi\s+dito",
    ]

    TOXIC_PATTERNS: ClassVar[list[str]] = [
        r"\b(exploit|ddos|sql\s*injection)\b",
    ]

    def sanitize_input(self, text: str) -> tuple[str, bool]:
        """Mask credit card PANs and CPFs from input text."""
        return sanitize_pii(text)

    def match_patterns(self, text: str) -> str | None:
        """Return "prompt_injection" when an INJECTION_PATTERNS entry matches the lowercased text,
        "attack_request" when a TOXIC_PATTERNS entry matches, else None. Injection is checked first."""
        low = text.lower()
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, low, re.IGNORECASE):
                return "prompt_injection"
        for pattern in self.TOXIC_PATTERNS:
            if re.search(pattern, low, re.IGNORECASE):
                return "attack_request"
        return None

    def evaluate_sync(self, state: AgentState) -> AgentState:
        """Evaluate safety of input and apply PII masking synchronously."""
        if not settings.ENABLE_GUARDRAILS:
            state.is_safe = True
            return state

        message = state.message.strip()

        if not message:
            state.is_safe = False
            state.safety_violations.append("Mensagem vazia.")
            state.agent_response = "Por favor, digite uma pergunta ou solicitação para que possamos te ajudar."
            state.final_agent = AgentRole.GUARDRAIL
            return state

        # 1. Apply PII Sanitization
        sanitized_msg, pii_found = self.sanitize_input(message)
        if pii_found:
            logger.info("PII masked in input")
            state.message = sanitized_msg

        # 2. Check for Prompt Injections / Attacks via Patterns
        category = self.match_patterns(sanitized_msg)
        if category == "prompt_injection":
            logger.warning(f"Guardrail pattern matched (category={category})")
            state.is_safe = False
            state.safety_violations.append("Tentativa de injeção de prompt ou violação de segurança detectada.")
            state.agent_response = (
                "Sua solicitação contém comandos não permitidos pelas nossas diretrizes de segurança. "
                "Por favor, reformule sua dúvida sobre os produtos e serviços da Getnet."
            )
            state.final_agent = AgentRole.GUARDRAIL
            return state

        if category == "attack_request":
            logger.warning(f"Guardrail pattern matched (category={category})")
            state.is_safe = False
            state.safety_violations.append("Termo de segurança malicioso detectado.")
            state.agent_response = "Solicitação bloqueada devido a termos não permitidos."
            state.final_agent = AgentRole.GUARDRAIL
            return state

        state.is_safe = True
        return state

    async def evaluate(self, state: AgentState) -> AgentState:
        """Async compatibility wrapper."""
        return self.evaluate_sync(state)
