"""Device-skill dispatcher (Priority #4 Milestone 7) -- the one shared
Brain-side path from "an authorized (node, skill, params)" to a signed
spine round trip. Used by both the DeviceAgent (low/medium-risk plan
steps) and the approval route (high-risk actions after NP-7 approval),
so the declaration check and audit write can never drift apart between
the two callers.

NP-5 enforcement lives here: the skill must be in the target node's LIVE
declared capabilities (DeviceStore.skills, recorded by the
chimera/+/capabilities subscriber) -- with the single built-in exception
of "ping", which every node answers regardless of declarations (matching
the node SDK's own built-in). There is no static skill table anywhere on
the Brain side; deleting a skill from a node's declaration removes it
from the dispatchable set with zero Brain code change.
"""

from __future__ import annotations

from dataclasses import dataclass

from devices.audit import DispatchAudit
from devices.store import DeviceStore
from mqtt import get_mqtt_client, send_command_and_await_response
from protocols.chimera_contract import ChimeraEnvelope


@dataclass
class DispatchOutcome:
    ok: bool
    detail: str
    result: dict | None = None


class DeviceDispatcher:
    def __init__(
        self,
        store: DeviceStore | None = None,
        audit: DispatchAudit | None = None,
    ) -> None:
        self.store = store or DeviceStore()
        self.audit = audit or DispatchAudit()

    def resolve_node(self, skill: str) -> str | None:
        """The node to dispatch `skill` to, from live declarations only:
        the (sorted-first) node currently declaring it. None when no node
        declares it."""
        declaring = sorted(
            d.node for d in self.store.list() if d.skills and skill in d.skills
        )
        return declaring[0] if declaring else None

    async def dispatch(
        self,
        *,
        node: str,
        skill: str,
        params: dict,
        risk: int,
        requester: str,
        key: str,
        approval_id: str | None = None,
        timeout: float = 15.0,
    ) -> DispatchOutcome:
        device = self.store.get(node)
        if device is None:
            self.audit.record(
                requester=requester, node=node, skill=skill, params=params,
                risk=risk, outcome="rejected_unknown_node", approval_id=approval_id,
            )
            return DispatchOutcome(False, f"unknown node {node!r}")

        if skill != "ping" and (device.skills is None or skill not in device.skills):
            self.audit.record(
                requester=requester, node=node, skill=skill, params=params,
                risk=risk, outcome="rejected_undeclared_skill", approval_id=approval_id,
            )
            return DispatchOutcome(
                False, f"node {node!r} does not declare skill {skill!r}"
            )

        client = get_mqtt_client()
        response: ChimeraEnvelope | None = await send_command_and_await_response(
            client, node, skill, params, key, timeout=timeout
        )
        if response is None:
            self.audit.record(
                requester=requester, node=node, skill=skill, params=params,
                risk=risk, outcome="timeout", approval_id=approval_id,
            )
            return DispatchOutcome(False, f"node {node!r} did not respond in time")

        self.audit.record(
            requester=requester, node=node, skill=skill, params=params,
            risk=risk, outcome="responded", approval_id=approval_id,
            result=response.params,
        )
        return DispatchOutcome(True, "responded", result=response.params)
