import asyncio

from events import EventBus, MemoryWritten, TurnCompleted, TurnStarted
from protocols import EnvelopeType


def test_sync_handler_receives_event():
    bus = EventBus()
    seen = []
    bus.subscribe(TurnStarted.TYPE, seen.append)
    bus.publish(TurnStarted(session_id="s1", user_input="hi"))
    assert len(seen) == 1
    assert seen[0].user_input == "hi"


def test_wildcard_handler_sees_everything():
    bus = EventBus()
    seen = []
    bus.subscribe("*", seen.append)
    bus.publish(TurnStarted(session_id="s1"))
    bus.publish(TurnCompleted(session_id="s1"))
    assert [e.TYPE for e in seen] == [EnvelopeType.TURN_STARTED, EnvelopeType.TURN_COMPLETED]


def test_unsubscribe():
    bus = EventBus()
    seen = []
    handler = bus.subscribe(TurnStarted.TYPE, seen.append)
    assert bus.unsubscribe(TurnStarted.TYPE, handler)
    assert not bus.unsubscribe(TurnStarted.TYPE, handler)
    bus.publish(TurnStarted())
    assert seen == []


def test_handler_exception_is_isolated():
    bus = EventBus()
    seen = []

    def boom(event):
        raise RuntimeError("handler bug")

    bus.subscribe(TurnStarted.TYPE, boom)
    bus.subscribe(TurnStarted.TYPE, seen.append)
    bus.publish(TurnStarted(user_input="still delivered"))
    assert len(seen) == 1


def test_async_handler_via_publish_without_loop():
    bus = EventBus()
    seen = []

    async def handler(event):
        seen.append(event)

    bus.subscribe(MemoryWritten.TYPE, handler)
    bus.publish(MemoryWritten(memory_id="m1"))
    assert len(seen) == 1


def test_async_handler_via_apublish():
    bus = EventBus()
    seen = []

    async def handler(event):
        seen.append(event)

    bus.subscribe(MemoryWritten.TYPE, handler)
    asyncio.run(bus.apublish(MemoryWritten(memory_id="m2")))
    assert len(seen) == 1
    assert seen[0].memory_id == "m2"


def test_event_to_envelope():
    event = MemoryWritten(session_id="s9", memory_id="m3", user_id="owner", origin="api")
    env = event.to_envelope(sequence=4)
    assert env.type == EnvelopeType.MEMORY_WRITTEN
    assert env.session == "s9"
    assert env.sequence == 4
    assert env.payload["memory_id"] == "m3"
    assert env.payload["user_id"] == "owner"
