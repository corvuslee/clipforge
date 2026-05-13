"""Event Bus implementation with Redis pub/sub."""

import asyncio
import json
from collections.abc import Callable
from typing import TYPE_CHECKING

import redis.asyncio as redis

from .schemas import Event, EventName, Payload, PublishError, SubscribeError

if TYPE_CHECKING:
    from redis.asyncio.client import PubSub


class EventBus:
    """Message hub for publishing/subscribing to events."""

    def __init__(self, redis_url: str = "redis://redis:6379") -> None:
        self._redis_url = redis_url
        self._redis: redis.Redis | None = None
        self._pubsub: PubSub | None = None
        self._subscribers: dict[EventName, list[Callable[[Event], None]]] = {}
        self._listener_task: asyncio.Task | None = None

    async def _connect(self) -> None:
        """Connect to Redis server."""
        self._redis = redis.from_url(self._redis_url, decode_responses=True)
        self._pubsub = self._redis.pubsub()

    async def publish(self, event_name: EventName, payload: Payload, turn: int) -> None:
        """Publish an event to all subscribers.

        Args:
            event_name: Name of the event to publish.
            payload: Event payload.
            turn: Current turn number.

        Raises:
            PublishError: If event publication fails.
        """
        if not self._redis:
            await self._connect()

        if not self._redis:
            raise PublishError("Failed to connect to Redis")

        try:
            event = Event(name=event_name, payload=payload, turn=turn)
            message = json.dumps(event.model_dump())
            await self._redis.publish(event_name.value, message)

            handlers = self._subscribers.get(event_name, [])
            for handler in handlers:
                handler(event)
        except Exception as e:
            raise PublishError(f"Failed to publish event '{event_name}': {e}") from e

    async def subscribe(
        self, event_name: EventName, handler: Callable[[Event], None]
    ) -> None:
        """Subscribe a handler to an event.

        Args:
            event_name: Name of the event to subscribe to.
            handler: Callable to invoke when event is published. Receives full Event object.

        Raises:
            SubscribeError: If subscription fails.
        """
        if not self._pubsub:
            await self._connect()

        if not self._pubsub:
            raise SubscribeError("Failed to connect to Redis")

        try:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
                await self._pubsub.subscribe(event_name.value)

            self._subscribers[event_name].append(handler)

            if not self._listener_task:
                self._listener_task = asyncio.create_task(self._listen())
        except Exception as e:
            raise SubscribeError(
                f"Failed to subscribe to event '{event_name}': {e}"
            ) from e

    async def unsubscribe(
        self, event_name: EventName, handler: Callable[[Event], None]
    ) -> None:
        """Unsubscribe a handler from an event.

        Args:
            event_name: Name of the event to unsubscribe from.
            handler: Callable to remove from subscribers.
        """
        try:
            handlers = self._subscribers.get(event_name, [])
            if handler in handlers:
                handlers.remove(handler)

            if not handlers and self._pubsub:
                await self._pubsub.unsubscribe(event_name.value)
                del self._subscribers[event_name]
        except Exception:
            pass

    async def _listen(self) -> None:
        """Listen for messages from Redis and call handlers."""
        if not self._pubsub:
            return

        try:
            async for message in self._pubsub.listen():
                if message["type"] != "message":
                    continue

                event_name_str = message["channel"]
                if isinstance(event_name_str, bytes):
                    event_name_str = event_name_str.decode()

                try:
                    event_name = EventName(event_name_str)
                except ValueError:
                    continue

                handlers = self._subscribers.get(event_name, [])
                if not handlers:
                    continue

                try:
                    data = json.loads(message["data"])
                    event = Event(**data)
                    for handler in handlers:
                        handler(event)
                except json.JSONDecodeError, Exception:
                    continue
        except asyncio.CancelledError:
            pass
