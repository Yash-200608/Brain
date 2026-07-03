"""Brain MQTT connectivity -- BrainMqttClient (Priority #3 Milestone 2),
the signed-envelope composition layer (Milestone 3), and the presence
handler (Milestone 5)."""
from .client import BrainMqttClient, get_mqtt_client, set_mqtt_client
from .presence import make_presence_handler
from .signed import publish_envelope, verify_payload

__all__ = [
    "BrainMqttClient",
    "get_mqtt_client",
    "set_mqtt_client",
    "publish_envelope",
    "verify_payload",
    "make_presence_handler",
]
