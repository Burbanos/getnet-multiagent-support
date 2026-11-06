"""Mock customer and operational database for customer support operations."""
from datetime import datetime, timedelta
from typing import Any


class MockDatabase:
    """In-memory realistic customer database for Getnet merchant accounts."""

    def __init__(self):
        self._init_data()

    def _init_data(self):
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        today_str = datetime.now().strftime("%Y-%m-%d")

        self.users: dict[str, dict[str, Any]] = {
            "cliente1988": {
                "user_id": "cliente1988",
                "trade_name": "Padaria & Confeitaria Central",
                "document": "12.345.678/0001-90",
                "contact_name": "Roberto Silva",
                "contact_email": "contato@padariacentral.com.br",
                "contact_phone": "+55 51 98877-6655",
                "plan": "Getnet Negócios Pro",
                "anticipation_type": "D+1 Automático",
                "pix_enabled": True,
                "bank_account": {
                    "bank": "Banco Santander (033)",
                    "agency": "1234",
                    "account": "98765-4",
                    "account_type": "Conta Corrente PJ"
                },
                "terminals": [
                    {
                        "serial_number": "GET-883921",
                        "model": "Get Smart",
                        "status": "ACTIVE",
                        "connection_type": "4G + Wi-Fi",
                        "sim_operator": "Claro",
                        "sim_status": "ONLINE",
                        "wifi_connected": False,
                        "signal_level": "Fraco / 1 barra",
                        "battery_level": "85%",
                        "firmware_version": "v4.2.1-prod",
                        "last_ping": "5 minutos atrás"
                    }
                ],
                "settlements": {
                    "yesterday_sales": {
                        "date": yesterday_str,
                        "total_transactions": 42,
                        "gross_amount": 3450.00,
                        "discounts_fees": 82.80,
                        "net_amount": 3367.20,
                        "settlement_date": today_str,
                        "estimated_deposit_time": "Até as 20h00 de hoje",
                        "status": "PROGRAMADO_PARA_HOJE",
                        "destination_account": "Santander (033) Ag: 1234 CC: 98765-4"
                    },
                    "accumulated_balance": 12840.50,
                    "available_for_anticipation": 9400.00
                },
                "recent_transactions": [
                    {
                        "transaction_id": "TXN-902188",
                        "timestamp": f"{today_str} 10:14:22",
                        "terminal_serial": "GET-883921",
                        "amount": 150.00,
                        "payment_method": "Cartão de Crédito - Mastercard",
                        "status": "DECLINED",
                        "error_code": "51",
                        "error_message": "Saldo ou limite insuficiente (Insuficient funds)",
                        "action_recommended": "Solicitar ao cliente final que utilize outro cartão ou verifique o limite disponível no aplicativo do banco emissor."
                    },
                    {
                        "transaction_id": "TXN-902187",
                        "timestamp": f"{today_str} 09:45:10",
                        "terminal_serial": "GET-883921",
                        "amount": 32.50,
                        "payment_method": "Débito - Visa",
                        "status": "APPROVED",
                        "error_code": None,
                        "error_message": None,
                        "action_recommended": None
                    }
                ]
            }
        }

        self.decline_code_catalog: dict[str, dict[str, str]] = {
            "51": {
                "name": "Saldo / Limite Insuficiente",
                "description": "O banco emissor do cartão recusou a transação por falta de saldo em conta ou limite de crédito.",
                "solution": "Peça ao cliente para tentar outro meio de pagamento (Pix, débito ou outro cartão) ou checar o app do banco."
            },
            "05": {
                "name": "Não Autorizada / Contate o Emissor",
                "description": "Bloqueio preventivo de segurança por parte do banco do cliente.",
                "solution": "O titular do cartão deve autorizar a compra no app do seu banco."
            },
            "57": {
                "name": "Transação Não Permitida para o Cartão",
                "description": "O cartão não possui a função habilitada (ex: compra internacional ou função crédito desativada).",
                "solution": "Pedir outro cartão habilitado para a função desejada."
            },
            "96": {
                "name": "Erro no Sistema / Timeout de Comunicação",
                "description": "Instabilidade temporária na bandeira ou na conexão do terminal com a adquirente.",
                "solution": "Aguarde 1 minuto e tente passar novamente, ou reinicie a máquina de cartão."
            }
        }

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Fetch user by id or create a dynamic fallback record if not exists."""
        if user_id in self.users:
            return self.users[user_id]
        
        # Dynamic fallback merchant so arbitrary user_ids can still test
        today_str = datetime.now().strftime("%Y-%m-%d")
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        return {
            "user_id": user_id,
            "trade_name": f"Estabelecimento {user_id}",
            "document": "00.000.000/0001-00",
            "contact_name": "Lojista Getnet",
            "contact_email": f"{user_id}@getnet-exemplo.com.br",
            "contact_phone": "+55 11 99999-0000",
            "plan": "Getnet Padrão",
            "anticipation_type": "D+1",
            "pix_enabled": True,
            "bank_account": {
                "bank": "Banco Santander (033)",
                "agency": "0001",
                "account": "12345-6",
                "account_type": "Conta Corrente PJ"
            },
            "terminals": [
                {
                    "serial_number": f"GET-{hash(user_id) % 1000000:06d}",
                    "model": "Get Smart",
                    "status": "ACTIVE",
                    "connection_type": "4G + Wi-Fi",
                    "sim_operator": "Vivo",
                    "sim_status": "ONLINE",
                    "wifi_connected": True,
                    "signal_level": "Bom / 3 barras",
                    "battery_level": "90%",
                    "firmware_version": "v4.2.1-prod",
                    "last_ping": "1 minuto atrás"
                }
            ],
            "settlements": {
                "yesterday_sales": {
                    "date": yesterday_str,
                    "total_transactions": 25,
                    "gross_amount": 1500.00,
                    "discounts_fees": 35.00,
                    "net_amount": 1465.00,
                    "settlement_date": today_str,
                    "estimated_deposit_time": "Até as 20h00 de hoje",
                    "status": "PROGRAMADO_PARA_HOJE",
                    "destination_account": "Banco Santander (033) Ag: 0001 CC: 12345-6"
                },
                "accumulated_balance": 4500.00,
                "available_for_anticipation": 3200.00
            },
            "recent_transactions": [
                {
                    "transaction_id": f"TXN-{hash(user_id) % 900000 + 100000}",
                    "timestamp": f"{today_str} 09:30:00",
                    "terminal_serial": f"GET-{hash(user_id) % 1000000:06d}",
                    "amount": 89.90,
                    "payment_method": "Crédito - Visa",
                    "status": "DECLINED",
                    "error_code": "51",
                    "error_message": "Saldo insuficiente",
                    "action_recommended": "Solicitar outro cartão ou pagamento via Pix."
                }
            ]
        }


# Global singleton instance
_mock_db_instance = MockDatabase()


def get_mock_db() -> MockDatabase:
    """Dependency getter for mock database."""
    return _mock_db_instance
