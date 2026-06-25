# api/infrastructure/events/dispatcher.py

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any, Final


EventPayload = dict[str, Any]
EventHandler = Callable[[EventPayload], None]

EventName = str
HandlerKey = str


_handlers: Final[defaultdict[EventName, list[EventHandler]]] = defaultdict(list)
_handler_keys: Final[defaultdict[EventName, set[HandlerKey]]] = defaultdict(set)


def _build_handler_key(handler: EventHandler) -> HandlerKey:
    """
    Builds a stable key for a handler.

    This prevents the same named handler from being registered multiple times
    when Django imports/reloads modules during development.
    """

    module_name = getattr(handler, "__module__", "")
    qualified_name = getattr(handler, "__qualname__", repr(handler))

    return f"{module_name}.{qualified_name}"


def register(
    event_name: str,
    handler: EventHandler,
) -> None:
    handler_key = _build_handler_key(handler)

    if handler_key in _handler_keys[event_name]:
        return

    _handlers[event_name].append(handler)
    _handler_keys[event_name].add(handler_key)


def dispatch(
    event_name: str,
    payload: EventPayload,
) -> None:
    handlers = tuple(_handlers.get(event_name, []))

    for handler in handlers:
        handler(payload)


__all__ = [
    "EventPayload",
    "EventHandler",
    "dispatch",
    "register",
]