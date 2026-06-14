"""Brain V2 protocol package — the single source of truth for wire formats."""
from .envelope import PROTOCOL_VERSION, Envelope, EnvelopeType, make_envelope, parse_envelope

__all__ = [
    "PROTOCOL_VERSION",
    "Envelope",
    "EnvelopeType",
    "make_envelope",
    "parse_envelope",
]
