"""Quick M11 spine smoke — invoke keystone skills via Brain API."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import settings  # noqa: E402


def _api_key() -> str:
    if settings.api_keys:
        return next(iter(settings.api_keys))
    raise SystemExit("no JARVIS_API_KEYS in .env")


def _post(path: str, body: dict) -> dict:
    url = f"http://127.0.0.1:{settings.api_port}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_api_key()}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode()}


def main() -> int:
    print("trial_start_ts:", settings.trial_start_ts)
    devices = json.loads(
        urllib.request.urlopen(
            urllib.request.Request(
                f"http://127.0.0.1:{settings.api_port}/api/devices/",
                headers={"Authorization": f"Bearer {_api_key()}"},
            ),
            timeout=15,
        ).read()
    )
    online = [d for d in devices if d.get("is_online") or d.get("online")]
    print("online nodes:", [d.get("node") or d.get("node_id") for d in online])
    phone = next(
        (d.get("node") or d.get("node_id") for d in online if "phone" in (d.get("node") or d.get("node_id") or "")),
        None,
    )
    pc = next(
        (d.get("node") or d.get("node_id") for d in online if "pc" in (d.get("node") or d.get("node_id") or "")),
        None,
    )
    if not phone:
        print("WARN: no online phone node")
    if not pc:
        print("WARN: no online pc node")

    tests = []
    if phone:
        tests += [
            (phone, "phone.battery", {}),
            (phone, "phone.app.open", {"app": "settings"}),
            (phone, "phone.sms.send", {"recipient": "+919876543210", "message": "M11 smoke"}),
        ]
    if pc:
        tests += [
            (pc, "ping", {}),
            (pc, "pc.media.control", {"command": "volume_up"}),
        ]

    for node, skill, params in tests:
        body = _post(f"/api/devices/{node}/invoke", {"skill": skill, "params": params})
        ok = body.get("result", {}).get("ok") if body.get("status") == "responded" else None
        print(f"{skill} @ {node}: status={body.get('status', body.get('_http_error'))} ok={ok}")
        if body.get("result", {}).get("error"):
            print("  error:", body["result"]["error"][:120])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
