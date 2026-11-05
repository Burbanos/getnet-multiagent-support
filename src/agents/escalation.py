"""Human Escalation Agent creating prioritized support tickets."""
import logging
import uuid
from src.core.state import AgentState, AgentRole

logger = logging.getLogger("multiagent.escalation")


class HumanEscalationAgent:
    """Creates support tickets and transfers conversation to human support specialists."""

    async def execute(self, state: AgentState) -> AgentState:
        ticket_id = f"GET-ESC-{uuid.uuid4().hex[:8].upper()}"
        state.escalate_to_human = True
        state.escalation_flag = True
        state.escalation_ticket_id = ticket_id
        state.tools_used.append("create_escalation_ticket")

        logger.info(f"Escalation ticket {ticket_id} created for user {state.user_id}")

        state.agent_response = (
            f"Entendi a sua solicitação. Transferi o seu atendimento para um especialista humano da nossa equipe.\n\n"
            f"• **Protocolo do Atendimento**: `{ticket_id}`\n"
            f"• **Tempo estimado de espera**: Menos de 5 minutos\n"
            f"• **Status**: Em fila prioritária de atendimento\n\n"
            "Um de nossos atendentes entrará em contato ou continuará este atendimento em instantes. "
            "Se preferir atendimento telefônico imediato, você também pode ligar para a Central Getnet no 4002-4000."
        )
        state.final_agent = AgentRole.ESCALATION
        return state
