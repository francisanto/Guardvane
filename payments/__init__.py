"""
Payment boundary for OpiHub service requests.

Payment is independent of Arkiv/Rabdi. Hedera x402 will plug into this package
later; this module never treats a wallet signature as proof of payment.
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
