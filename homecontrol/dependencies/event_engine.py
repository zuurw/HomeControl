"""EventEngine for HomeControl"""

from contextlib import suppress
from typing import List, Callable, Any
import asyncio
import logging
from collections import defaultdict
from datetime import datetime

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class Event:
    """Representation for an Event"""

    __slots__ = ["event_type", "data", "timestamp", "kwargs"]

    def __init__(self,
                 event_type: str,
                 data: dict = None,
                 timestamp: int = None,
                 kwargs: dict = None) -> None:

        self.event_type = event_type
        self.data = data or {}
        self.timestamp = timestamp or datetime.now()
        self.kwargs = kwargs or {}

    def __repr__(self) -> str:
        return f"<Event {self.event_type} kwargs={self.kwargs}>  {self.data}"


class EventEngine:
    """Dispatcher for events"""
    def __init__(self, core) -> None:
        self.core = core
        self.handlers = defaultdict(set)

    def broadcast(self,  # lgtm [py/similar-function]
                  event_type: str,
                  data: dict = None,
                  **kwargs) -> List[asyncio.Future]:
        """
        Broadcast an event and return the futures

        Every listener is a coroutine that will simply
        receive event and `kwargs`

        Example:
        >>> async def on_event(event: Event, ...):
        >>>     return
        """

        data = data or {}
        data.update(kwargs)
        event = Event(event_type, data=data, timestamp=datetime.now())

        LOGGER.debug("Event: %s", event)

        handlers = (
            list(self.handlers.get("*", list()))
            + list(self.handlers.get(event_type, list()))
        )

        return [asyncio.ensure_future(
            handler(event, **kwargs),
            loop=self.core.loop) for handler in handlers]

    def broadcast_threaded(self,  # lgtm [py/similar-function]
                           event_type: str,
                           data: dict = None,
                           **kwargs) -> List[asyncio.Task]:
        """
        Same as broadcast BUT
        - It returns Futures and not Tasks
        - It uses threads
        """
        data = data or {}
        data.update(kwargs)
        event = Event(event_type, data=data, timestamp=datetime.now())

        LOGGER.debug("Event: %s", event)

        handlers = (
            list(self.handlers.get("*", list()))
            + list(self.handlers.get(event_type, list()))
        )

        return [asyncio.run_coroutine_threadsafe(
            handler(event, **kwargs),
            loop=self.core.loop) for handler in handlers]

    async def gather(self,
                     event_type: str,
                     data: dict = None,
                     **kwargs) -> List[Any]:
        """
        Broadcast an event and return the results
        """
        return await asyncio.gather(
            *self.broadcast(event_type, data, **kwargs))

    def register(self, event: str) -> Callable:
        """
        Decorator to register event handlers

        :param event:
        :return:
        """
        def _register(coro):
            self.handlers[event].add(coro)
            return coro
        return _register

    def remove_handler(self, event: str, handler: callable) -> None:
        """
        Removes an event handler
        """
        with suppress(KeyError):
            self.handlers[event].remove(handler)
