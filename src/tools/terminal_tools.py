"""Terminal diagnostics and troubleshooting tools for POS card machines."""
import logging
from typing import Dict, Any, Optional
from src.core.mock_db import get_mock_db

logger = logging.getLogger("multiagent.terminal_tools")


def diagnose_terminal_connectivity(user_id: str, terminal_serial: Optional[str] = None) -> Dict[str, Any]:
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

    steps = [
        "Reinicie o terminal mantendo o botão liga/desliga pressionado por 5 segundos.",
        "No menu do Get Smart, acesse 'Configurações' > 'Rede' e verifique se o chip Claro/Vivo está ativado.",
        "Se estiver em local fechado com sinal fraco, conecte o terminal à sua rede Wi-Fi 2.4GHz.",
        "Realize um teste de conexão em 'Menu Lojista' > 'Comunicação' > 'Teste de Conexão'."
    ]

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
        "diagnosis": "Conexão de chip 4G com sinal instável na localidade. Recomenda-se ativar o Wi-Fi ou reiniciar a máquina.",
        "troubleshooting_steps": steps
    }
