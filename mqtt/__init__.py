"""Brain MQTT connectivity -- BrainMqttClient (Priority #3 Milestone 2),
the signed-envelope composition layer (Milestone 3), the presence handler
(Milestone 5), the state handler (Milestone 7), the command round-trip
helper (Milestone 8), and the capabilities handler (Priority #4
Milestone 4)."""
from .capabilities import make_capabilities_handler
from .client import BrainMqttClient, get_mqtt_client, set_mqtt_client
from .presence import make_presence_handler
from .signed import publish_envelope, send_command_and_await_response, verify_payload
from .state import make_state_handler

__all__ = [
    "BrainMqttClient",
    "get_mqtt_client",
    "set_mqtt_client",
    "publish_envelope",
    "verify_payload",
    "send_command_and_await_response",
    "make_presence_handler",
    "make_state_handler",
    "make_capabilities_handler",
]
