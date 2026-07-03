"""Brain V2 protocol package — the single source of truth for wire formats."""
from .chimera_contract import CONTRACT_VERSION, ChimeraEnvelope, RiskTier, sign, verify
from .envelope import PROTOCOL_VERSION, Envelope, EnvelopeType, make_envelope, parse_envelope

__all__ = [
    "PROTOCOL_VERSION",
    "Envelope",
    "EnvelopeType",
    "make_envelope",
    "parse_envelope",
    "CONTRACT_VERSION",
    "ChimeraEnvelope",
    "RiskTier",
    "sign",
    "verify",
]
