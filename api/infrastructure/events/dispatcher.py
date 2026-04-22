 # api/infrastructure/events/dispatcher.py
 
# The purpose of this file is to be the central event bus of your application.

# It is the component that:
# stores which handlers listen to which events
# and executes those handlers when an event happens

# Think of it like this:

# Something happens → dispatch(event)
#                  → dispatcher finds handlers
#                  → dispatcher executes handlers

from collections import defaultdict
from typing import Callable, Dict, List, Any


EventPayload = dict[str, Any]


_handlers: Dict[str, List[Callable[[EventPayload], None]]] = defaultdict(list)


def register(
    event_name: str,
    handler: Callable[[EventPayload], None],
) -> None:
    _handlers[event_name].append(handler)


def dispatch(
    event_name: str,
    payload: EventPayload,
) -> None:
    handlers = _handlers.get(event_name, [])

    for handler in handlers:
        handler(payload)
