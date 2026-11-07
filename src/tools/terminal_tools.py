"""Terminal diagnostics and troubleshooting tools for POS card machines."""
import logging
from typing import Any

from src.core.mock_db import get_mock_db

logger = logging.getLogger("multiagent.terminal_tools")


def diagnose_terminal_connectivity(user_id: str, terminal_serial: str | None = None) -> dict[str, Any]:
    """
    Diagnose POS card machine connectivity issues (4G/Wi-Fi, SIM card, signal).
    
    Args:
        user_id: Merchant identifier.
        terminal_serial: Optional terminal serial number.
        
    Returns:
        Diagnostic results and recommended step-by-step troubleshooting actions.
    """
    db = get_mock_db()
    user = db.get_user(user_id)
    if not user:
        return {"error": f"Lojista '{user_id}' não encontrado."}

    terminals = user.get("terminals", [])
    if not terminals:
        return {"error": "Nenhuma máquina de cartão vinculada a este estabelecimento."}

    terminal = terminals[0]
    if terminal_serial:
        for t in terminals:
            if t.get("serial_number") == terminal_serial:
                terminal = t
                break

    model = terminal.get("model")
    sim_operator = terminal.get("sim_operator")
    sim_status = (terminal.get("sim_status") or "").strip().lower()
    signal_level = (terminal.get("signal_level") or "").strip().lower()
    wifi_connected = bool(terminal.get("wifi_connected"))

    sinal_fraco = ("fraco" in signal_level or "sem sinal" in signal_level) and not wifi_connected

    steps: list[str] = []
    if model:
        steps.append(f"Reinicie o terminal {model} mantendo o botão liga/desliga pressionado por 5 segundos.")
    else:
        steps.append("Reinicie o terminal mantendo o botão liga/desliga pressionado por 5 segundos.")

    has_issue = False

    if sinal_fraco:
        has_issue = True
        if sim_operator:
            steps.append(f"Em Configurações > Rede, verifique se o chip {sim_operator} está ativo.")
        else:
            steps.append("Em Configurações > Rede, verifique se o chip está ativo.")
        steps.append("Conecte o terminal a uma rede Wi-Fi 2.4GHz.")

    if sim_status and sim_status not in ("ativo", "active", "online"):
        has_issue = True
        if sim_operator:
            steps.append(f"Verifique a situação do chip com a operadora {sim_operator}.")
        else:
            steps.append("Verifique a situação do chip com a operadora.")

    steps.append("Faça um teste de conexão no menu do terminal.")

    if sinal_fraco:
        diagnosis = "Sinal móvel baixo e Wi-Fi desconectado."
    elif has_issue:
        diagnosis = f"Problema identificado na conectividade do chip ({terminal.get('sim_status')})."
    else:
        diagnosis = "Nenhum problema de conectividade identificado na telemetria do terminal."

    return {
        "status": "success",
        "user_id": user_id,
        "terminal_model": terminal.get("model"),
        "serial_number": terminal.get("serial_number"),
        "operational_status": terminal.get("status"),
        "connection_type": terminal.get("connection_type"),
        "sim_operator": terminal.get("sim_operator"),
        "sim_status": terminal.get("sim_status"),
        "wifi_connected": terminal.get("wifi_connected"),
        "signal_level": terminal.get("signal_level"),
        "battery_level": terminal.get("battery_level"),
        "diagnosis": diagnosis,
        "troubleshooting_steps": steps,
    }
