"""Unit tests for TurnManager."""

import asyncio

import pytest
import pytest_asyncio

from fakeredis.aioredis import FakeRedis

from src.events.bus import EventBus
from src.events.schemas import (
    EmptyPayload,
    Event,
    EventName,
    PurchasingStateReportedPayload,
    InventoryStateReportedPayload,
    FactoryStateReportedPayload,
    MarketStateReportedPayload,
)
from src.modules.turn_manager import MODULES, Phase, TurnManager


@pytest_asyncio.fixture
async def event_bus():
    """Create a connected EventBus with fake Redis."""
    bus = EventBus()
    fake_redis = FakeRedis(decode_responses=True)
    bus._redis = fake_redis
    bus._pubsub = fake_redis.pubsub()
    yield bus


@pytest_asyncio.fixture
async def turn_manager(event_bus):
    """Create a TurnManager with fake EventBus."""
    manager = TurnManager(event_bus=event_bus)
    yield manager


class TestAutoStart:
    """Tests for auto-start behavior."""

    @pytest.mark.asyncio
    async def test_start_emits_plan_phase_started(self, turn_manager, event_bus):
        """Starting TM emits plan_phase_started on turn 1."""
        event = asyncio.Event()

        def handler(evt: Event):
            event.set()

        await event_bus.subscribe(EventName.PLAN_PHASE_STARTED, handler)
        await turn_manager.start()

        await asyncio.wait_for(event.wait(), timeout=0.5)

    @pytest.mark.asyncio
    async def test_start_sets_turn_counter_to_1(self, turn_manager):
        """Turn counter is 1 after start."""
        await turn_manager.start()
        assert turn_manager.turn_counter == 1

    @pytest.mark.asyncio
    async def test_start_sets_phase_to_planning(self, turn_manager):
        """Phase is PLANNING after start."""
        await turn_manager.start()
        assert turn_manager.current_phase == Phase.PLANNING


class TestPlanningWindow:
    """Tests for planning window behavior."""

    @pytest.mark.asyncio
    async def test_planning_window_opens_after_all_state_reports(
        self, turn_manager, event_bus
    ):
        """planning_window_opened only after all 4 modules report state."""
        event = asyncio.Event()

        def handler(evt: Event):
            event.set()

        await event_bus.subscribe(EventName.PLANNING_WINDOW_OPENED, handler)
        await turn_manager.start()

        # Simulate state reports from modules (planning window not yet opened)
        await event_bus.publish(
            EventName.PURCHASING_STATE_REPORTED,
            PurchasingStateReportedPayload(
                fund=0, wire_cost=20.0, autoclipper_cost=50.0
            ),
            turn=1,
        )
        await event_bus.publish(
            EventName.INVENTORY_STATE_REPORTED,
            InventoryStateReportedPayload(wire=150, unsold_clips=0, total_clips=0),
            turn=1,
        )
        await event_bus.publish(
            EventName.FACTORY_STATE_REPORTED,
            FactoryStateReportedPayload(auto_clippers=1),
            turn=1,
        )

        # Fourth report triggers planning window
        await event_bus.publish(
            EventName.MARKET_STATE_REPORTED,
            MarketStateReportedPayload(price=0.05),
            turn=1,
        )

        await asyncio.wait_for(event.wait(), timeout=0.5)


class TestPhaseTransitions:
    """Tests for phase transition logic."""

    @pytest.mark.asyncio
    async def test_plan_phase_completed_triggers_action_phase(
        self, turn_manager, event_bus
    ):
        """plan_phase_completed from external agent triggers action_phase_started."""
        event = asyncio.Event()

        def handler(evt: Event):
            event.set()

        await event_bus.subscribe(EventName.ACTION_PHASE_STARTED, handler)

        # Report all states to open planning window
        await turn_manager.start()
        await event_bus.publish(
            EventName.PURCHASING_STATE_REPORTED,
            PurchasingStateReportedPayload(
                fund=0, wire_cost=20.0, autoclipper_cost=50.0
            ),
            turn=1,
        )
        await event_bus.publish(
            EventName.INVENTORY_STATE_REPORTED,
            InventoryStateReportedPayload(wire=150, unsold_clips=0, total_clips=0),
            turn=1,
        )
        await event_bus.publish(
            EventName.FACTORY_STATE_REPORTED,
            FactoryStateReportedPayload(auto_clippers=1),
            turn=1,
        )
        await event_bus.publish(
            EventName.MARKET_STATE_REPORTED,
            MarketStateReportedPayload(price=0.05),
            turn=1,
        )

        # External agent completes planning
        await event_bus.publish(EventName.PLAN_PHASE_COMPLETED, EmptyPayload(), turn=1)

        await asyncio.wait_for(event.wait(), timeout=0.5)
        assert turn_manager.current_phase == Phase.ACTION

    @pytest.mark.asyncio
    async def test_all_action_completions_triggers_turn_end(
        self, turn_manager, event_bus
    ):
        """All module action_completions trigger action_phase_completed and next turn."""
        event = asyncio.Event()

        def handler(evt: Event):
            event.set()

        await event_bus.subscribe(EventName.ACTION_PHASE_COMPLETED, handler)

        # Setup: get to action phase
        await turn_manager.start()
        await event_bus.publish(
            EventName.PURCHASING_STATE_REPORTED,
            PurchasingStateReportedPayload(
                fund=0, wire_cost=20.0, autoclipper_cost=50.0
            ),
            turn=1,
        )
        await event_bus.publish(
            EventName.INVENTORY_STATE_REPORTED,
            InventoryStateReportedPayload(wire=150, unsold_clips=0, total_clips=0),
            turn=1,
        )
        await event_bus.publish(
            EventName.FACTORY_STATE_REPORTED,
            FactoryStateReportedPayload(auto_clippers=1),
            turn=1,
        )
        await event_bus.publish(
            EventName.MARKET_STATE_REPORTED,
            MarketStateReportedPayload(price=0.05),
            turn=1,
        )

        await event_bus.publish(EventName.PLAN_PHASE_COMPLETED, EmptyPayload(), turn=1)

        # Simulate action completions (fourth triggers turn end)
        await event_bus.publish(
            EventName.PURCHASING_ACTION_COMPLETED, EmptyPayload(), turn=1
        )
        await event_bus.publish(
            EventName.INVENTORY_ACTION_COMPLETED, EmptyPayload(), turn=1
        )
        await event_bus.publish(
            EventName.FACTORY_ACTION_COMPLETED, EmptyPayload(), turn=1
        )
        await event_bus.publish(
            EventName.MARKET_ACTION_COMPLETED, EmptyPayload(), turn=1
        )

        await asyncio.wait_for(event.wait(), timeout=0.5)
        assert turn_manager.turn_counter == 2
        assert turn_manager.current_phase == Phase.PLANNING


class TestStaleEventRejection:
    """Tests for rejecting stale events from old turns."""

    @pytest.mark.asyncio
    async def test_stale_state_reports_ignored(self, turn_manager, event_bus):
        """State reports from old turns are ignored."""
        event = asyncio.Event()

        def handler(evt: Event):
            event.set()

        await event_bus.subscribe(EventName.PLANNING_WINDOW_OPENED, handler)
        await turn_manager.start()

        # Simulate being on turn 2
        turn_manager._turn_counter = 2
        turn_manager._pending_state_reports = MODULES.copy()

        # Send 3 valid turn 2 reports and 1 stale turn 1 report
        await event_bus.publish(
            EventName.PURCHASING_STATE_REPORTED,
            PurchasingStateReportedPayload(
                fund=0, wire_cost=20.0, autoclipper_cost=50.0
            ),
            turn=2,
        )
        await event_bus.publish(
            EventName.INVENTORY_STATE_REPORTED,
            InventoryStateReportedPayload(wire=150, unsold_clips=0, total_clips=0),
            turn=2,
        )
        await event_bus.publish(
            EventName.FACTORY_STATE_REPORTED,
            FactoryStateReportedPayload(auto_clippers=1),
            turn=1,
        )
        await event_bus.publish(
            EventName.MARKET_STATE_REPORTED,
            MarketStateReportedPayload(price=0.05),
            turn=2,
        )

        # Planning window should NOT open (only 3 valid reports received)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(event.wait(), timeout=0.1)

        # Send the 4th valid turn 2 report
        await event_bus.publish(
            EventName.FACTORY_STATE_REPORTED,
            FactoryStateReportedPayload(auto_clippers=1),
            turn=2,
        )

        await asyncio.wait_for(event.wait(), timeout=0.5)

    @pytest.mark.asyncio
    async def test_stale_action_completions_ignored(self, turn_manager, event_bus):
        """Action completions from old turns are ignored."""
        event = asyncio.Event()

        def handler(evt: Event):
            event.set()

        await event_bus.subscribe(EventName.ACTION_PHASE_COMPLETED, handler)
        await turn_manager.start()

        # Simulate being in action phase on turn 2
        turn_manager._turn_counter = 2
        turn_manager._current_phase = Phase.ACTION
        turn_manager._pending_action_completions = MODULES.copy()

        # Send 3 valid turn 2 completions and 1 stale turn 1 completion
        await event_bus.publish(
            EventName.PURCHASING_ACTION_COMPLETED, EmptyPayload(), turn=2
        )
        await event_bus.publish(
            EventName.INVENTORY_ACTION_COMPLETED, EmptyPayload(), turn=1
        )
        await event_bus.publish(
            EventName.FACTORY_ACTION_COMPLETED, EmptyPayload(), turn=2
        )
        await event_bus.publish(
            EventName.MARKET_ACTION_COMPLETED, EmptyPayload(), turn=2
        )

        # Turn should NOT end (only 3 valid completions received)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(event.wait(), timeout=0.1)

        # Send the 4th valid turn 2 completion
        await event_bus.publish(
            EventName.INVENTORY_ACTION_COMPLETED, EmptyPayload(), turn=2
        )

        await asyncio.wait_for(event.wait(), timeout=0.5)
