"""API tools — sandboxed outbound HTTP."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import requests

from tools.base import Tool

ALLOWED_SCHEMES = {"https"}


class HTTPGetTool(Tool):
    def __init__(self, allowed_hosts: set[str] | None = None) -> None:
        super().__init__(
            name="http.get",
            description="HTTPS GET against an allowed host.",
            input_schema={"url": "str"},
        )
        self.allowed_hosts = allowed_hosts or set()

    def run(self, *, url: str, **_: Any) -> dict:
        parsed = urlparse(url)
        if parsed.scheme not in ALLOWED_SCHEMES:
            raise ValueError(f"scheme {parsed.scheme} not allowed")
        if self.allowed_hosts and parsed.hostname not in self.allowed_hosts:
            raise ValueError(f"host {parsed.hostname} not allowed")
        r = requests.get(url, timeout=20)
        return {"status": r.status_code, "headers": dict(r.headers), "body": r.text[:5000]}
