from typing import Any

import pytest

from agents.executor import ExecutorAgent
from modelgw import (
    ModelGateway,
    ModelProvider,
    ModelProviderError,
    OllamaProvider,
    get_model_gateway,
    set_model_gateway,
)


class FakeProvider(ModelProvider):
    name = "fake"

    def __init__(self, response: str = "fake-out", *, fail: bool = False) -> None:
        self.response = response
        self.fail = fail
        self.calls: list[dict[str, Any]] = []

    def generate(self, *, model, system, prompt, temperature=0.2, options=None) -> str:
        self.calls.append(
            {"model": model, "system": system, "prompt": prompt,
             "temperature": temperature, "options": options}
        )
        if self.fail:
            raise ModelProviderError("backend down")
        return self.response


@pytest.fixture(autouse=True)
def _reset_gateway():
    yield
    set_model_gateway(None)


def test_default_gateway_uses_ollama():
    set_model_gateway(None)
    gw = get_model_gateway()
    assert isinstance(gw.provider(), OllamaProvider)


def test_gateway_routes_to_named_provider():
    fake = FakeProvider("hello")
    gw = ModelGateway({"fake": fake}, default="fake")
    out = gw.generate(model="m", system="s", prompt="p", temperature=0.7)
    assert out == "hello"
    assert fake.calls[0]["temperature"] == 0.7


def test_gateway_unknown_provider_raises():
    gw = ModelGateway({"fake": FakeProvider()}, default="fake")
    with pytest.raises(ModelProviderError):
        gw.generate(model="m", system="s", prompt="p", provider="nope")


def test_ollama_provider_request_shape(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "pong"}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("modelgw.ollama.requests.post", fake_post)
    provider = OllamaProvider(base_url="http://test:1234")
    out = provider.generate(model="m1", system="sys", prompt="hi", temperature=0.3,
                            options={"num_ctx": 2048})
    assert out == "pong"
    assert captured["url"] == "http://test:1234/api/generate"
    assert captured["json"]["model"] == "m1"
    assert captured["json"]["stream"] is False
    assert captured["json"]["options"] == {"temperature": 0.3, "num_ctx": 2048}
    assert captured["timeout"] == 120


def test_agent_call_returns_empty_on_provider_error():
    """V1 compat: a failed LLM call yields '' — never an exception."""
    set_model_gateway(ModelGateway({"fake": FakeProvider(fail=True)}, default="fake"))
    agent = ExecutorAgent()
    assert agent.call("hello") == ""


def test_agent_call_passes_through_gateway():
    fake = FakeProvider("result text")
    set_model_gateway(ModelGateway({"fake": fake}, default="fake"))
    agent = ExecutorAgent()
    assert agent.call("hello") == "result text"
    assert fake.calls[0]["model"] == agent.model
    assert fake.calls[0]["system"] == agent.system_prompt
