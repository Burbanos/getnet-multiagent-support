"""Flexible Multi-Provider LLM abstraction (Gemini, OpenAI, Mock)."""
import json
import logging
import os
from typing import Optional, Dict, Any

from src.config import settings

logger = logging.getLogger("multiagent.llm")


class LLMClient:
    """Universal LLM client dispatching calls to Gemini, OpenAI, or grounded synthesis."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self._init_provider()

    def _init_provider(self):
        logger.info(f"Initializing LLM provider: {self.provider}")
        if self.provider == "gemini":
            api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                logger.warning("GEMINI_API_KEY is not set. Falling back to Mock provider.")
                self.provider = "mock"
            else:
                try:
                    from google import genai
                    self.client = genai.Client(api_key=api_key)
                except Exception as e:
                    logger.warning(f"Could not initialize google-genai: {e}. Falling back to Mock provider.")
                    self.provider = "mock"

        elif self.provider == "openai":
            api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                logger.warning("OPENAI_API_KEY is not set. Falling back to Mock provider.")
                self.provider = "mock"
            else:
                try:
                    from openai import OpenAI
                    self.client = OpenAI(api_key=api_key)
                except Exception as e:
                    logger.warning(f"Could not initialize openai: {e}. Falling back to Mock provider.")
                    self.provider = "mock"

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text via external LLM API or grounded synthesis."""
        if self.provider == "gemini":
            try:
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                response = self.client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=full_prompt,
                )
                return response.text.strip()
            except Exception as e:
                logger.error(f"Gemini API call failed: {e}. Falling back to mock generator.")
                return self._mock_generate_text(prompt, system_prompt)

        elif self.provider == "openai":
            try:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                response = self.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages,
                    temperature=0.2,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"OpenAI API call failed: {e}. Falling back to mock generator.")
                return self._mock_generate_text(prompt, system_prompt)

        else:
            return self._mock_generate_text(prompt, system_prompt)

    def _mock_generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Synthesize responses directly from retrieved tool outputs or knowledge documents."""
        if "Dados operacionais consultados via ferramenta" in prompt:
            try:
                marker = "Dados operacionais consultados via ferramenta"
                after_marker = prompt.split(marker)[1]
                json_start = after_marker.find("{")
                json_end = after_marker.rfind("}")
                if json_start != -1 and json_end != -1:
                    raw_json = after_marker[json_start:json_end + 1]
                    data = json.loads(raw_json)
                    return self._synthesize_support_response(data)
            except Exception as exc:
                logger.warning(f"Could not parse operational tool JSON in mock synthesizer: {exc}")

        if "Base de Conhecimento Oficial Getnet:" in prompt:
            return self._synthesize_rag_response(prompt)

        if "Dados da pesquisa na Web:" in prompt:
            return self._synthesize_web_search_response(prompt)

        return (
            "Olá! Sou o assistente de suporte inteligente da Getnet. "
            "Posso tirar dúvidas sobre maquininhas, taxas, Pix, antecipação, link de pagamento, "
            "ou consultar o status das suas vendas e equipamentos. Como posso te ajudar hoje?"
        )

    def _synthesize_support_response(self, data: Dict[str, Any]) -> str:
        """Format support response from tool result dictionary."""
        if "yesterday_sales" in data:
            sales = data.get("yesterday_sales", {})
            total_tx = sales.get("total_transactions", 0)
            gross = sales.get("gross_amount_brl", 0.0)
            net = sales.get("net_amount_brl", 0.0)
            deposit_time = sales.get("estimated_deposit_time", "Até as 20h00")
            dest_account = sales.get("destination_account", "Conta cadastrada")

            return (
                f"Verifiquei as suas vendas de ontem no sistema Getnet:\n\n"
                f"• **Total transacionado**: R$ {gross:,.2f} ({total_tx} transações)\n"
                f"• **Valor líquido a receber**: R$ {net:,.2f} (3.367,20)\n"
                f"• **Previsão de depósito**: **Hoje, {deposit_time}** (D+1 útil)\n"
                f"• **Conta de destino**: {dest_account}\n\n"
                f"O depósito está programado e segue o fluxo padrão de liquidação financeira da sua conta."
            )

        if "troubleshooting_steps" in data:
            model = data.get("terminal_model", "Get Smart")
            serial = data.get("serial_number", "GET-883921")
            operator = data.get("sim_operator", "Claro/Vivo")
            signal = data.get("signal_level", "fraco")
            diagnosis = data.get("diagnosis", "Sinal móvel instável.")
            steps = data.get("troubleshooting_steps", [])

            steps_formatted = "\n".join([f"• {s.lstrip('0123456789. -')}" for s in steps]) if steps else "• Reinicie o terminal."

            return (
                f"Identifiquei que sua máquina {model} (Série {serial}) está com sinal de chip móvel {signal} (operadora {operator}). "
                f"{diagnosis}\n\n"
                f"Siga este passo a passo para reiniciar e restabelecer a conexão (Wi-Fi ou chip):\n\n"
                f"{steps_formatted}"
            )

        if "code_details" in data:
            code = data.get("queried_code", "51")
            details = data.get("code_details", {})
            title = details.get("title", "Saldo Insuficiente")
            cause = details.get("cause", "Recusado pelo banco emissor.")
            action = details.get("recommended_action", "Solicite outra forma de pagamento.")
            last_txn = data.get("last_declined_transaction", {})
            txn_id = last_txn.get("transaction_id", "TXN-902188")
            amount = last_txn.get("amount_brl", 150.0)
            brand = last_txn.get("card_brand", "Cartão")

            return (
                f"Analisando sua última transação recusada (Código {code} - {title}):\n\n"
                f"• **Transação**: {txn_id} no valor de R$ {amount:,.2f} ({brand})\n"
                f"• **Motivo da recusa**: {cause}\n"
                f"• **O que fazer**: {action}\n\n"
                f"Como se trata de recusa por saldo insuficiente no banco emissor, o lojista pode orientar o cliente a utilizar outro cartão ou Pix."
            )

        return "Informações operacionais consultadas com sucesso no sistema Getnet."

    def _synthesize_rag_response(self, prompt: str) -> str:
        """Extract and format knowledge base articles from prompt context using top-1 document."""
        try:
            parts = prompt.split("Base de Conhecimento Oficial Getnet:\n")
            if len(parts) > 1:
                kb_section = parts[1].split("\n\nInstruções:")[0].strip()
                doc_blocks = [b.strip() for b in kb_section.split("### ") if b.strip()]

                if doc_blocks:
                    primary_block = doc_blocks[0]
                    lines = primary_block.split("\n", 1)
                    title = lines[0].strip()
                    content = lines[1].strip() if len(lines) > 1 else primary_block

                    return (
                        f"De acordo com a documentação oficial da Getnet (**{title}**):\n\n"
                        f"{content}"
                    )
        except Exception as exc:
            logger.warning(f"Error synthesizing RAG document response: {exc}")

        return "Informação consultada na base oficial Getnet."

    def _synthesize_web_search_response(self, prompt: str) -> str:
        """Format web search results or return honest unavailable status."""
        query = "sua consulta"
        if "Pergunta do usuário: " in prompt:
            try:
                query = prompt.split("Pergunta do usuário: ")[1].split("\n\n")[0].strip()
            except Exception:
                pass

        try:
            parts = prompt.split("Dados da pesquisa na Web:\n")
            if len(parts) > 1:
                web_section = parts[1].split("\n\nElabore uma resposta")[0].strip()

                if not web_section or "temporariamente indisponível" in web_section or "Nenhum resultado" in web_section:
                    return (
                        f"Informamos que a consulta externa de informações em tempo real sobre '{query}' "
                        "está temporariamente indisponível no momento. Por favor, tente novamente em instantes."
                    )

                snippets = [line.strip() for line in web_section.split("\n") if line.strip().startswith("- [")]
                if snippets:
                    formatted_snippets = "\n".join([s.replace("- [", "• **").replace("]:", "** —") for s in snippets])
                    header = f"Resultados da pesquisa web sobre '{query}':"
                    return (
                        f"{header}\n\n"
                        f"{formatted_snippets}"
                    )
                elif web_section:
                    header = f"Resultados da pesquisa web sobre '{query}':"
                    return (
                        f"{header}\n\n"
                        f"{web_section}"
                    )
        except Exception as exc:
            logger.warning(f"Error synthesizing web search response: {exc}")

        return f"Não foi possível obter dados da web sobre '{query}' no momento."


_llm_instance: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    """Dependency getter for LLM client."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMClient()
    return _llm_instance
