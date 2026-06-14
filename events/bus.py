"""EventBus — in-process, async-compatible pub/sub.

Design rules:
  * Handler failures are logged and isolated; the bus never breaks a turn.
  * Handlers may be plain callables or coroutine functions.
  * ``publish`` is safe from synchronous code (no running loop required);
    ``apublish`` is the awaitable variant for async callers and runs async
    handlers to completion before returning.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import threading
from collections import defaultdict
from typing import Any, Callable

from events.types import Event

logger = logging.getLogger(__name__)

Handler = Callable[[Event], Any]

WILDCARD = "*"


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._lock = threading.RLock()

    # -- subscription --
    def subscribe(self, event_type: str, handler: Handler) -> Handler:
        """Register ``handler`` for ``event_type`` (or ``"*"`` for all events).

        Returns the handler so callers can keep a reference for unsubscribe.
        """
        with self._lock:
            self._subscribers[event_type].append(handler)
        return handler

    def unsubscribe(self, event_type: str, handler: Handler) -> bool:
        with self._lock:
            handlers = self._subscribers.get(event_type, [])
            try:
                handlers.remove(handler)
                return True
            except ValueError:
                return False

    # -- publication --
    def publish(self, event: Event) -> None:
        """Dispatch from synchronous code.

        Sync handlers run inline. Async handlers run to completion via a
        private loop when no loop is running in this thread; if a loop IS
        running they are scheduled on it (fire-and-forget).
        """
        for handler in self._handlers_for(event):
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    self._dispatch_awaitable(result, event)
            except Exception:  # noqa: BLE001 - bus must never break the caller
                logger.exception("event handler failed for %s", event.TYPE)

    async def apublish(self, event: Event) -> None:
        """Dispatch from async code; awaits async handlers to completion."""
        for handler in self._handlers_for(event):
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
            except Exception:  # noqa: BLE001
                logger.exception("event handler failed for %s", event.TYPE)

    # -- internals --
    def _handlers_for(self, event: Event) -> list[Handler]:
        with self._lock:
            return list(self._subscribers.get(event.TYPE, [])) + list(
                self._subscribers.get(WILDCARD, [])
            )

    @staticmethod
    def _dispatch_awaitable(awaitable: Any, event: Event) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(_await_safely(awaitable, event.TYPE))
        else:
            loop.create_task(_await_safely(awaitable, event.TYPE))


async def _await_safely(awaitable: Any, event_type: str) -> None:
    try:
        await awaitable
    except Exception:  # noqa: BLE001
        logger.exception("async event handler failed for %s", event_type)


_bus: EventBus | None = None
_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """Process-wide default bus."""
    global _bus
    if _bus is None:
        with _bus_lock:
            if _bus is None:
                _bus = EventBus()
    return _bus


def set_event_bus(bus: EventBus | None) -> None:
    """Replace the default bus (primarily for tests)."""
    global _bus
    with _bus_lock:
        _bus = bus
