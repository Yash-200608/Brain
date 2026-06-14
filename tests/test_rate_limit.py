import asyncio
import time

from starlette.requests import Request
from starlette.responses import PlainTextResponse

from api.middleware.rate_limit import RateLimitMiddleware


def _request(ip: str = "1.2.3.4") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "client": (ip, 1234),
    }
    return Request(scope)


async def _ok(_request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def test_blocks_after_threshold():
    mw = RateLimitMiddleware(None, rate=3, per_seconds=60)

    async def run():
        for _ in range(3):
            r = await mw.dispatch(_request(), _ok)
            assert r.status_code == 200
        r = await mw.dispatch(_request(), _ok)
        assert r.status_code == 429

    asyncio.run(run())


def test_separate_clients_independent():
    mw = RateLimitMiddleware(None, rate=1, per_seconds=60)

    async def run():
        assert (await mw.dispatch(_request("1.1.1.1"), _ok)).status_code == 200
        assert (await mw.dispatch(_request("2.2.2.2"), _ok)).status_code == 200
        assert (await mw.dispatch(_request("1.1.1.1"), _ok)).status_code == 429

    asyncio.run(run())


def test_prunes_stale_buckets():
    mw = RateLimitMiddleware(None, rate=10, per_seconds=1)
    old = time.time() - 60
    for i in range(1100):
        mw._buckets[f"10.0.{i // 256}.{i % 256}"] = [old]

    asyncio.run(mw.dispatch(_request("9.9.9.9"), _ok))
    assert len(mw._buckets) < 1100
