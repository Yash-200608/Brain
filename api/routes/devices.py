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
from api.schemas import DeviceOut, InvokeIn
from config import settings
from devices.approvals import ApprovalStore, principal_key
from devices.audit import DispatchAudit
from devices.dispatcher import DeviceDispatcher
from devices.models import Device
from devices.policy import skill_risk_int
from devices.store import DeviceStore
from identity import (
    SCOPE_DEVICES_ACTION,
    SCOPE_DEVICES_APPROVE,
    SCOPE_DEVICES_READ,
    Principal,
)
from mqtt import get_mqtt_client, send_command_and_await_response
from trial.report import build_trial_report

router = APIRouter()
_store = DeviceStore()
_approvals = ApprovalStore()
_audit = DispatchAudit()
_dispatcher = DeviceDispatcher(store=_store, audit=_audit)


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


# -- approvals + audit (Priority #4 Milestone 7) ---------------------------
# NOTE: these static paths MUST be registered before the /{node} route
# below, or FastAPI would happily treat "approvals" as a node name.


@router.get(
    "/approvals",
    dependencies=[Depends(require_scope(SCOPE_DEVICES_READ))],
)
def list_approvals() -> list[dict]:
    return [
        {
            "id": a.id,
            "node": a.node,
            "skill": a.skill,
            "params": a.params,
            "risk": a.risk,
            "created_at": a.created_at,
        }
        for a in _approvals.list_pending()
    ]


@router.post("/approvals/{approval_id}/approve")
async def approve_and_dispatch(
    approval_id: str,
    approver: Principal = Depends(require_scope(SCOPE_DEVICES_APPROVE)),
) -> dict:
    """Consumes the approval (single-use, NP-7 property 3) and dispatches
    the EXACT stored action instance -- never anything from this request's
    body, so an approver cannot be tricked into approving a swapped action
    (property 2). The store rejects an approver whose identity tuple equals
    the requester's (property 1); the scope gate above enforces
    privileged-above (devices.approve is not in default_scopes).
    """
    if not settings.mqtt_enabled or not settings.mqtt_hmac_key:
        raise HTTPException(503, "mqtt not enabled/configured on this Brain instance")

    approver_key = principal_key(
        approver.user_id, approver.client_id, approver.metadata.get("key_id")
    )
    pending = _approvals.get(approval_id)
    if pending is None:
        raise HTTPException(404, "approval not found (unknown or already used)")

    approval = _approvals.consume(approval_id, approver_key)
    if approval is None:
        raise HTTPException(
            403, "approver must be a principal distinct from the requester"
        )

    outcome = await _dispatcher.dispatch(
        node=approval.node,
        skill=approval.skill,
        params=approval.params,
        risk=approval.risk,
        requester=approval.requester,
        key=settings.mqtt_hmac_key,
        approval_id=approval.id,
    )
    if not outcome.ok:
        raise HTTPException(504 if "respond" in outcome.detail else 502, outcome.detail)
    return {
        "approval_id": approval.id,
        "node": approval.node,
        "skill": approval.skill,
        "result": outcome.result,
    }


@router.post(
    "/approvals/{approval_id}/deny",
    dependencies=[Depends(require_scope(SCOPE_DEVICES_APPROVE))],
)
def deny_approval(approval_id: str) -> dict:
    if not _approvals.deny(approval_id):
        raise HTTPException(404, "approval not found")
    return {"denied": approval_id}


@router.get(
    "/audit",
    dependencies=[Depends(require_scope(SCOPE_DEVICES_READ))],
)
def list_audit(limit: int = 50) -> list[dict]:
    return _audit.list(limit=limit)


@router.get(
    "/trial-report",
    dependencies=[Depends(require_scope(SCOPE_DEVICES_READ))],
)
def trial_report() -> dict:
    """M11 trial instrumentation — spine audit aggregates plus legacy log."""
    return build_trial_report(
        _audit,
        legacy_log_path=settings.trial_legacy_log_path,
        since_ts=settings.trial_start_ts,
    )


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


@router.post("/{node}/invoke")
async def invoke_skill(
    node: str,
    payload: InvokeIn,
    requester: Principal = Depends(require_scope(SCOPE_DEVICES_ACTION)),
) -> dict:
    """Direct skill invocation (Priority #4 Milestone 10) -- the dashboard
    command console's surface onto the SAME machinery as the NL path:
    risk classified by Brain's policy first (NP-7 property 2); risk >= 2
    creates a pending approval (202) for a distinct approver instead of
    executing; anything else dispatches through the shared dispatcher,
    which enforces live declarations (NP-5) and writes the audit trail.
    """
    if not settings.mqtt_enabled or not settings.mqtt_hmac_key:
        raise HTTPException(503, "mqtt not enabled/configured on this Brain instance")

    requester_key = principal_key(
        requester.user_id, requester.client_id, requester.metadata.get("key_id")
    )
    risk = skill_risk_int(payload.skill)

    if risk >= 2:
        approval = _approvals.request(
            node=node, skill=payload.skill, params=payload.params,
            risk=risk, requester=requester_key,
        )
        _audit.record(
            requester=requester_key, node=node, skill=payload.skill,
            params=payload.params, risk=risk, outcome="approval_requested",
            approval_id=approval.id,
        )
        return {
            "status": "approval_required",
            "approval_id": approval.id,
            "risk": risk,
        }

    outcome = await _dispatcher.dispatch(
        node=node, skill=payload.skill, params=payload.params, risk=risk,
        requester=requester_key, key=settings.mqtt_hmac_key,
    )
    if not outcome.ok:
        raise HTTPException(504 if "respond" in outcome.detail else 502, outcome.detail)
    return {"status": "responded", "node": node, "skill": payload.skill, "result": outcome.result}


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
