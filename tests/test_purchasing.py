"""Unit tests for Purchasing module."""

import asyncio

import pytest
import pytest_asyncio

from fakeredis.aioredis import FakeRedis

from src.events.bus import EventBus
from src.events.schemas import (
    AutoclipperPurchaseApprovedPayload,
    BuyAutoclipperPayload,
    BuyWirePayload,
    ClipsSoldPayload,
    EmptyPayload,
    Event,
    EventName,
    InsufficientFundsError,
    PurchasingStateReportedPayload,
    WirePurchaseApprovedPayload,
)
from src.modules.purchasing import Purchasing
from src.utils.constants import AutoclipperCost, InitialState


@pytest_asyncio.fixture
async def event_bus():
    """Create a connected EventBus with fake Redis."""
    bus = EventBus()
    fake_redis = FakeRedis(decode_responses=True)
    bus._redis = fake_redis
    bus._pubsub = fake_redis.pubsub()
    yield bus


@pytest_asyncio.fixture
async def purchasing(event_bus):
    """Create a Purchasing with fake EventBus."""
    purchasing = Purchasing(event_bus=event_bus)
    await purchasing.start()
    yield purchasing


class TestInitialState:
    """Tests for initial state values."""

    def test_initial_fund(self, purchasing):
        """Fund starts at InitialState.FUND (0)."""
        assert purchasing.fund == InitialState.FUND

    def test_initial_wire_cost(self, purchasing):
        """Wire cost starts at InitialState.WIRE_COST (20.0)."""
        assert purchasing.wire_cost == InitialState.WIRE_COST

    def test_initial_autoclipper_cost(self, purchasing):
        """Autoclipper cost starts at InitialState.AUTOCLIPPER_COST (50.0)."""
        assert purchasing.autoclipper_cost == AutoclipperCost.AUTOCLIPPER_BASE_COST


class TestAddFunds:
    """Tests for adding funds."""

    def test_add_funds_increases_balance(self, purchasing):
        """add_funds increases the fund balance."""
        purchasing.add_funds(100)
        assert purchasing.fund == 100

    def test_add_funds_accumulates(self, purchasing):
        """Multiple add_funds calls accumulate."""
        purchasing.add_funds(50)
        purchasing.add_funds(30)
        assert purchasing.fund == 80


class TestRemoveFundsForWire:
    """Tests for wire purchase logic."""

    def test_remove_funds_for_wire_success(self, purchasing):
        """Wire purchase deducts funds and returns count purchased."""
        purchasing.add_funds(100)
        result = purchasing.remove_funds_for_wire(2)
        assert result == 2

    def test_remove_funds_for_wire_insufficient_funds(self, purchasing):
        """Wire purchase with zero funds raises error."""
        with pytest.raises(InsufficientFundsError):
            purchasing.remove_funds_for_wire(1)


class TestRemoveFundsForAutoclipper:
    """Tests for autoclipper purchase logic."""

    def test_remove_funds_for_autoclipper_success(self, purchasing):
        """Autoclipper purchase deducts funds and returns count purchased."""
        purchasing.add_funds(200)
        result = purchasing.remove_funds_for_autoclipper(1)
        assert result == 1

    def test_remove_funds_for_autoclipper_insufficient_funds(self, purchasing):
        """Autoclipper purchase with zero funds raises error."""
        with pytest.raises(InsufficientFundsError):
            purchasing.remove_funds_for_autoclipper(1)


class TestEventSubscriptions:
    """Tests for event subscription and handling."""

    @pytest.mark.asyncio
    async def test_plans_phase_started_reports_state(self, purchasing, event_bus):
        """plan_phase_started triggers purchasing_state_reported."""
        event = asyncio.Event()
        reported_fund = None

        def handler(evt: Event):
            nonlocal reported_fund
            payload = PurchasingStateReportedPayload(**evt.payload.model_dump())
            reported_fund = payload.fund
            event.set()

        await event_bus.subscribe(EventName.PURCHASING_STATE_REPORTED, handler)

        purchasing.add_funds(100)
        await event_bus.publish(EventName.PLAN_PHASE_STARTED, EmptyPayload(), turn=1)

        await asyncio.wait_for(event.wait(), timeout=0.5)
        assert reported_fund == 100

    @pytest.mark.asyncio
    async def test_buy_wire_queues_single_purchase(self, purchasing, event_bus):
        """buy_wire event queues purchase for action phase."""
        plan_event = asyncio.Event()

        def plan_handler(evt: Event):
            plan_event.set()

        await event_bus.subscribe(EventName.PURCHASING_STATE_REPORTED, plan_handler)
        await event_bus.publish(EventName.PLAN_PHASE_STARTED, EmptyPayload(), turn=1)
        await asyncio.wait_for(plan_event.wait(), timeout=0.5)

        await event_bus.publish(EventName.BUY_WIRE, BuyWirePayload(count=2), turn=1)
        await asyncio.sleep(0.05)

        assert purchasing._pending_wire_purchases == [2]

    @pytest.mark.asyncio
    async def test_buy_wire_queues_multiple_purchases(self, purchasing, event_bus):
        """Multiple buy_wire events queue multiple purchases."""
        plan_event = asyncio.Event()

        def plan_handler(evt: Event):
            plan_event.set()

        await event_bus.subscribe(EventName.PURCHASING_STATE_REPORTED, plan_handler)
        await event_bus.publish(EventName.PLAN_PHASE_STARTED, EmptyPayload(), turn=1)
        await asyncio.wait_for(plan_event.wait(), timeout=0.5)

        await event_bus.publish(EventName.BUY_WIRE, BuyWirePayload(count=2), turn=1)
        await event_bus.publish(EventName.BUY_WIRE, BuyWirePayload(count=3), turn=1)
        await asyncio.sleep(0.05)

        assert purchasing._pending_wire_purchases == [2, 3]

    @pytest.mark.asyncio
    async def test_buy_autoclipper_queues_single_purchase(self, purchasing, event_bus):
        """buy_autoclipper event queues purchase for action phase."""
        plan_event = asyncio.Event()

        def plan_handler(evt: Event):
            plan_event.set()

        await event_bus.subscribe(EventName.PURCHASING_STATE_REPORTED, plan_handler)
        await event_bus.publish(EventName.PLAN_PHASE_STARTED, EmptyPayload(), turn=1)
        await asyncio.wait_for(plan_event.wait(), timeout=0.5)

        await event_bus.publish(
            EventName.BUY_AUTOCLIPPER, BuyAutoclipperPayload(count=1), turn=1
        )
        await asyncio.sleep(0.05)

        assert purchasing._pending_autoclipper_purchases == [1]

    @pytest.mark.asyncio
    async def test_buy_autoclipper_queues_multiple_purchases(
        self, purchasing, event_bus
    ):
        """Multiple buy_autoclipper events queue multiple purchases."""
        plan_event = asyncio.Event()

        def plan_handler(evt: Event):
            plan_event.set()

        await event_bus.subscribe(EventName.PURCHASING_STATE_REPORTED, plan_handler)
        await event_bus.publish(EventName.PLAN_PHASE_STARTED, EmptyPayload(), turn=1)
        await asyncio.wait_for(plan_event.wait(), timeout=0.5)

        await event_bus.publish(
            EventName.BUY_AUTOCLIPPER, BuyAutoclipperPayload(count=1), turn=1
        )
        await event_bus.publish(
            EventName.BUY_AUTOCLIPPER, BuyAutoclipperPayload(count=2), turn=1
        )
        await asyncio.sleep(0.05)

        assert purchasing._pending_autoclipper_purchases == [1, 2]

    @pytest.mark.asyncio
    async def test_action_phase_processes_wire_purchase(self, purchasing, event_bus):
        """action_phase_started processes queued wire purchase."""
        plan_event = asyncio.Event()

        def plan_handler(evt: Event):
            plan_event.set()

        await event_bus.subscribe(EventName.PURCHASING_STATE_REPORTED, plan_handler)
        await event_bus.publish(EventName.PLAN_PHASE_STARTED, EmptyPayload(), turn=1)
        await asyncio.wait_for(plan_event.wait(), timeout=0.5)

        event = asyncio.Event()
        approved_count = None

        def handler(evt: Event):
            nonlocal approved_count
            payload = WirePurchaseApprovedPayload(**evt.payload.model_dump())
            approved_count = payload.count
            event.set()

        await event_bus.subscribe(EventName.WIRE_PURCHASE_APPROVED, handler)

        purchasing.add_funds(60)
        await event_bus.publish(EventName.BUY_WIRE, BuyWirePayload(count=2), turn=1)
        await event_bus.publish(EventName.ACTION_PHASE_STARTED, EmptyPayload(), turn=1)

        await asyncio.wait_for(event.wait(), timeout=0.5)
        assert approved_count == 2

    @pytest.mark.asyncio
    async def test_action_phase_processes_autoclipper_purchase(
        self, purchasing, event_bus
    ):
        """action_phase_started processes queued autoclipper purchase."""
        plan_event = asyncio.Event()

        def plan_handler(evt: Event):
            plan_event.set()

        await event_bus.subscribe(EventName.PURCHASING_STATE_REPORTED, plan_handler)
        await event_bus.publish(EventName.PLAN_PHASE_STARTED, EmptyPayload(), turn=1)
        await asyncio.wait_for(plan_event.wait(), timeout=0.5)

        event = asyncio.Event()
        approved_count = None

        def handler(evt: Event):
            nonlocal approved_count
            payload = AutoclipperPurchaseApprovedPayload(**evt.payload.model_dump())
            approved_count = payload.count
            event.set()

        await event_bus.subscribe(EventName.AUTOCLIPPER_PURCHASE_APPROVED, handler)

        purchasing.add_funds(100)
        await event_bus.publish(
            EventName.BUY_AUTOCLIPPER, BuyAutoclipperPayload(count=1), turn=1
        )
        await event_bus.publish(EventName.ACTION_PHASE_STARTED, EmptyPayload(), turn=1)

        await asyncio.wait_for(event.wait(), timeout=0.5)
        assert approved_count == 1

    @pytest.mark.asyncio
    async def test_action_phase_emits_action_completed(self, purchasing, event_bus):
        """action_phase_started emits purchasing_action_completed."""
        event = asyncio.Event()

        def handler(evt: Event):
            event.set()

        await event_bus.subscribe(EventName.PURCHASING_ACTION_COMPLETED, handler)

        await event_bus.publish(EventName.ACTION_PHASE_STARTED, EmptyPayload(), turn=1)

        await asyncio.wait_for(event.wait(), timeout=0.5)

    @pytest.mark.asyncio
    async def test_clips_sold_adds_revenue(self, purchasing, event_bus):
        """clips_sold event adds revenue to fund."""
        event = asyncio.Event()

        def handler(evt: Event):
            event.set()

        await event_bus.subscribe(EventName.CLIPS_SOLD, handler)
        purchasing.add_funds(50)
        await event_bus.publish(
            EventName.CLIPS_SOLD, ClipsSoldPayload(clips=10, revenue=30), turn=1
        )

        await asyncio.wait_for(event.wait(), timeout=0.5)
        assert purchasing.fund == 80


class TestPlanPhaseClearsQueues:
    """Tests for purchase queue clearing on plan phase."""

    @pytest.mark.asyncio
    async def test_plan_phase_started_clears_queues(self, purchasing, event_bus):
        """plan_phase_started clears pending purchases."""
        event = asyncio.Event()

        def handler(evt: Event):
            event.set()

        await event_bus.subscribe(EventName.PURCHASING_STATE_REPORTED, handler)

        await event_bus.publish(EventName.BUY_WIRE, BuyWirePayload(count=1), turn=1)
        await event_bus.publish(
            EventName.BUY_AUTOCLIPPER, BuyAutoclipperPayload(count=1), turn=1
        )

        await event_bus.publish(EventName.PLAN_PHASE_STARTED, EmptyPayload(), turn=2)

        await asyncio.wait_for(event.wait(), timeout=0.5)
        assert len(purchasing._pending_wire_purchases) == 0
        assert len(purchasing._pending_autoclipper_purchases) == 0


class TestTurnValidation:
    """Tests for turn validation on external agent events."""

    @pytest.mark.asyncio
    async def test_buy_wire_rejected_wrong_turn(self, purchasing, event_bus):
        """buy_wire with wrong turn is rejected."""
        plan_event = asyncio.Event()

        def plan_handler(evt: Event):
            plan_event.set()

        await event_bus.subscribe(EventName.PURCHASING_STATE_REPORTED, plan_handler)
        await event_bus.publish(EventName.PLAN_PHASE_STARTED, EmptyPayload(), turn=1)
        await asyncio.wait_for(plan_event.wait(), timeout=0.5)

        await event_bus.publish(EventName.BUY_WIRE, BuyWirePayload(count=2), turn=2)
        await asyncio.sleep(0.05)

        assert len(purchasing._pending_wire_purchases) == 0

    @pytest.mark.asyncio
    async def test_buy_autoclipper_rejected_wrong_turn(self, purchasing, event_bus):
        """buy_autoclipper with wrong turn is rejected."""
        plan_event = asyncio.Event()

        def plan_handler(evt: Event):
            plan_event.set()

        await event_bus.subscribe(EventName.PURCHASING_STATE_REPORTED, plan_handler)
        await event_bus.publish(EventName.PLAN_PHASE_STARTED, EmptyPayload(), turn=1)
        await asyncio.wait_for(plan_event.wait(), timeout=0.5)

        await event_bus.publish(
            EventName.BUY_AUTOCLIPPER, BuyAutoclipperPayload(count=1), turn=2
        )
        await asyncio.sleep(0.05)

        assert len(purchasing._pending_autoclipper_purchases) == 0

    @pytest.mark.asyncio
    async def test_buy_wire_rejected_before_plan_phase(self, purchasing, event_bus):
        """buy_wire before plan_phase_started is rejected (current_turn=0)."""
        await event_bus.publish(EventName.BUY_WIRE, BuyWirePayload(count=2), turn=1)
        await asyncio.sleep(0.05)

        assert len(purchasing._pending_wire_purchases) == 0
