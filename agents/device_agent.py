"""DeviceAgent -- executes a device-skill plan step over the execution
spine (Priority #4 Milestone 7).

Thin by design: the task's `extra` carries {skill, params} decided by
Brain's planning layer (core/device_intents.py today); this agent resolves
the target node from LIVE declarations, dispatches through the shared
DeviceDispatcher, and reports the node's truthful answer. High-risk
(risk >= 2) device tasks never reach this agent -- the pipeline's existing
risk gate blocks them and the approval flow (api/routes/devices.py) is the
only path that can execute them, after NP-7 approval.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from agents.protocol import AgentResult, AgentStatus
from config import settings
from devices.approvals import principal_key
from devices.dispatcher import DeviceDispatcher

if TYPE_CHECKING:
    from core.context import TurnContext
    from core.task import Task


class DeviceAgent:
    name = "device"

    def __init__(self, dispatcher: DeviceDispatcher | None = None) -> None:
        self.dispatcher = dispatcher or DeviceDispatcher()

    async def run(self, task: "Task", context: "TurnContext") -> AgentResult:
        skill = task.extra.get("skill", "")
        params = task.extra.get("params", {})
        if not skill:
            return AgentResult(status=AgentStatus.ERROR, output="device task has no skill")

        if not settings.mqtt_enabled or not settings.mqtt_hmac_key:
            return AgentResult(
                status=AgentStatus.ERROR,
                output="mqtt not enabled/configured on this Brain instance",
            )

        node = task.extra.get("node") or self.dispatcher.resolve_node(skill)
        if node is None:
            return AgentResult(
                status=AgentStatus.ERROR,
                output=f"no connected node declares skill {skill!r}",
            )

        principal = context.principal
        requester = principal_key(
            principal.user_id if principal else "unknown",
            principal.client_id if principal else "unknown",
            (principal.metadata.get("key_id") if principal else None),
        )

        outcome = await self.dispatcher.dispatch(
            node=node,
            skill=skill,
            params=params,
            risk=task.risk,
            requester=requester,
            key=settings.mqtt_hmac_key,
        )
        if not outcome.ok:
            return AgentResult(status=AgentStatus.ERROR, output=outcome.detail)
        return AgentResult(
            status=AgentStatus.OK,
            output=f"{skill} on {node}: {json.dumps(outcome.result)}",
            metadata={"node": node, "skill": skill, "result": outcome.result},
        )
