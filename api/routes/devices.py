"""/api/devices routes -- read-only exposure of DeviceStore
(Priority #3 Milestone 9), plus a single device-level action, ping
(Priority #3 Milestone 12 -- the Execution Spine Capstone's "at least one
real command demonstrated end-to-end" requirement, exposed through the
Dashboard/API leg of that path).

Scope enforcement (Priority #4 Milestone 1): the read routes require
`devices.read`; the ping action requires `devices.action` -- the
consequential device-level operation PRIORITY-2-READINESS-REVIEW.md named
as the scope-enforcement trigger. The deferral flagged here through
Priority #3 is now resolved: every route below carries an explicit scope
check, wired in the same coherent pass as query/memory/goals/sessions.
Later P4 milestones' skill-dispatch and approval endpoints reuse
`devices.action` (or an approval-specific scope) the same way.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import require_scope
from api.schemas import DeviceOut
from config import settings
from devices.models import Device
from devices.store import DeviceStore
from identity import SCOPE_DEVICES_ACTION, SCOPE_DEVICES_READ
from mqtt import get_mqtt_client, send_command_and_await_response

router = APIRouter()
_store = DeviceStore()


def _to_out(d: Device) -> DeviceOut:
    return DeviceOut(
        node=d.node,
        first_seen=d.first_seen,
        last_seen=d.last_seen,
        state=d.state,
        last_state_at=d.last_state_at,
        skills=d.skills,
        skills_declared_at=d.skills_declared_at,
        is_online=d.is_online(),
    )


@router.get(
    "/",
    response_model=list[DeviceOut],
    dependencies=[Depends(require_scope(SCOPE_DEVICES_READ))],
)
def list_devices() -> list[DeviceOut]:
    return [_to_out(d) for d in _store.list()]


@router.get(
    "/{node}",
    response_model=DeviceOut,
    dependencies=[Depends(require_scope(SCOPE_DEVICES_READ))],
)
def get_device(node: str) -> DeviceOut:
    d = _store.get(node)
    if d is None:
        raise HTTPException(404, "device not found")
    return _to_out(d)


@router.post(
    "/{node}/ping",
    dependencies=[Depends(require_scope(SCOPE_DEVICES_ACTION))],
)
async def ping_device(node: str) -> dict:
    """Sends the "ping" dummy command (jarvis_node_sdk.command_handler,
    Milestone 6/8) to `node` over the live MQTT round trip and returns its
    response -- the minimal HTTP door onto an already-existing capability,
    not a new action. This is the "at least one real command" leg of the
    Execution Spine Capstone's Dashboard/API -> Brain -> MQTT -> JARVIS ->
    Response -> Brain -> Dashboard/API path.
    """
    if not settings.mqtt_enabled or not settings.mqtt_hmac_key:
        raise HTTPException(503, "mqtt not enabled/configured on this Brain instance")

    client = get_mqtt_client()
    response = await send_command_and_await_response(
        client, node, "ping", {}, settings.mqtt_hmac_key, timeout=10.0
    )
    if response is None:
        raise HTTPException(504, f"device {node!r} did not respond in time")
    return {"node": node, "action": "ping", "result": response.params}
