"""
Payment boundary for OpiHub service requests.

Direct 0G AI reasoning for automated agents; EVM Smart Escrow on Rabdi Testnet for specialists.
"""

from payments.gateway import PaymentGateway, PaymentIntent, get_payment_gateway
from payments.service import payment_service, PaymentService

__all__ = [
    "PaymentGateway",
    "PaymentIntent",
    "get_payment_gateway",
    "payment_service",
    "PaymentService",
]
