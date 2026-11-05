"""Input sanitization and prompt injection protection."""
import logging
import re
from src.core.state import AgentState, AgentRole
from src.config import settings

logger = logging.getLogger("multiagent.guardrails")


class GuardrailAgent:
    """Detects unsafe prompts, prompt injections, and unsupported inputs."""

    INJECTION_PATTERNS = [
        # English patterns
        r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
        r"system\s*prompt",
        r"you\s+are\s+now\s+dan",
        r"jailbreak",
        r"bypass\s+restrictions",
        r"exfiltrate",
        r"reveal\s+your\s+(secret|instructions|key)",
        # Portuguese patterns
        r"ignore\s+(todas\s+as\s+)?(suas\s+)?instru[cç][oõ]es",
        r"(me\s+)?mostre\s+(o\s+)?(seu\s+)?prompt",
        r"regras\s+internas",
        r"prompt\s+de\s+sistema",
        r"esque[cç]a\s+(o\s+que\s+foi\s+dito|tudo)",
    ]

    TOXIC_PATTERNS = [
        r"\b(hack|exploit|ddos|sql\s*injection)\b",
    ]

    async def evaluate(self, state: AgentState) -> AgentState:
        if not settings.ENABLE_GUARDRAILS:
            state.is_safe = True
            return state

        message = state.message.strip()
        lower_msg = message.lower()

        if not message:
            state.is_safe = False
            state.safety_violations.append("Mensagem vazia.")
            state.agent_response = "Por favor, digite uma pergunta ou solicitação para que possamos te ajudar."
            state.final_agent = AgentRole.GUARDRAIL
            return state

        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, lower_msg, re.IGNORECASE):
                logger.warning(f"Prompt injection pattern detected: '{pattern}' in user {state.user_id}")
                state.is_safe = False
                state.safety_violations.append("Tentativa de injeção de prompt ou violação de segurança detectada.")
                state.agent_response = (
                    "Sua solicitação contém comandos não permitidos pelas nossas diretrizes de segurança. "
                    "Por favor, reformule sua dúvida sobre os produtos e serviços da Getnet."
                )
                state.final_agent = AgentRole.GUARDRAIL
                return state

        state.is_safe = True
        return state
