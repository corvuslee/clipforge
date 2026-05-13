"""Unit tests for EventBus."""

import pytest
import pytest_asyncio

from fakeredis.aioredis import FakeRedis

from src.events.bus import EventBus
from src.events.schemas import (
    EventName,
    Event,
    BuyWirePayload,
    EmptyPayload,
)


@pytest_asyncio.fixture
async def event_bus():
    """Create a connected EventBus with fake Redis."""
    bus = EventBus()
    fake_redis = FakeRedis(decode_responses=True)
    bus._redis = fake_redis
    bus._pubsub = fake_redis.pubsub()
    yield bus


class TestPublish:
    """Tests for publish() method."""

    @pytest.mark.asyncio
    async def test_publish_event_to_redis(self, event_bus):
        """Published events are sent to Redis pub/sub."""
        payload = EmptyPayload()

        await event_bus.publish(EventName.PLAN_PHASE_STARTED, payload, turn=1)
        # Success = no exception raised


class TestSubscribe:
    """Tests for subscribe() method."""

    @pytest.mark.asyncio
    async def test_subscribe_registers_multiple_handlers(self, event_bus):
        """Multiple handlers can subscribe to the same event."""
        handler1 = lambda e: None
        handler2 = lambda e: None

        await event_bus.subscribe(EventName.PLAN_PHASE_STARTED, handler1)
        await event_bus.subscribe(EventName.PLAN_PHASE_STARTED, handler2)

        assert len(event_bus._subscribers[EventName.PLAN_PHASE_STARTED]) == 2
        assert handler1 in event_bus._subscribers[EventName.PLAN_PHASE_STARTED]
        assert handler2 in event_bus._subscribers[EventName.PLAN_PHASE_STARTED]


class TestUnsubscribe:
    """Tests for unsubscribe() method."""

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_handler(self, event_bus):
        """Handler is removed from subscribers."""
        handler = lambda e: None
        await event_bus.subscribe(EventName.PLAN_PHASE_STARTED, handler)

        await event_bus.unsubscribe(EventName.PLAN_PHASE_STARTED, handler)

        assert handler not in event_bus._subscribers.get(EventName.PLAN_PHASE_STARTED, [])


class TestEventDelivery:
    """Tests for event delivery flow."""

    @pytest.mark.asyncio
    async def test_subscriber_receives_published_event(self, event_bus):
        """Full cycle: subscribe → publish → handler called."""
        received = []

        def handler(evt: Event):
            received.append(evt)

        await event_bus.subscribe(EventName.BUY_WIRE, handler)
        payload = BuyWirePayload(count=50)

        await event_bus.publish(EventName.BUY_WIRE, payload, turn=1)

        assert len(received) == 1
        assert received[0].payload.count == 50
        assert received[0].turn == 1

    @pytest.mark.asyncio
    async def test_no_subscriber_no_error(self, event_bus):
        """Publishing without subscribers doesn't raise."""
        payload = EmptyPayload()

        await event_bus.publish(EventName.PLAN_PHASE_STARTED, payload, turn=1)
        # No exception = pass
