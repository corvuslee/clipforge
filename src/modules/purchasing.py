"""Purchasing module for managing funds, costs, and purchase transactions."""

import random

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
from src.utils.constants import AutoclipperCost, InitialState, WireCost


class Purchasing:
    """Manages funds, costs, and purchase transactions."""

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._fund: int = InitialState.FUND
        self._wire_cost: float = InitialState.WIRE_COST
        self._autoclipper_count: int = 0
        self._pending_wire_purchases: list[int] = []
        self._pending_autoclipper_purchases: list[int] = []
        self._current_turn: int = 0

    @property
    def fund(self) -> int:
        """Current fund balance."""
        return self._fund

    @property
    def wire_cost(self) -> float:
        """Current wire cost per spool."""
        return self._wire_cost

    @property
    def autoclipper_cost(self) -> float:
        """Current autoclipper cost for next purchase."""
        return AutoclipperCost.AUTOCLIPPER_BASE_COST * (
            AutoclipperCost.AUTOCLIPPER_GROWTH_RATE**self._autoclipper_count
        )

    def add_funds(self, amount: int) -> None:
        """Add funds to purchasing."""
        self._fund += amount

    def _process_purchase(
        self, count: int, unit_cost: float, item_name: str
    ) -> tuple[int, int]:
        """Calculate affordable count and total cost for a purchase.

        Args:
            count: Number of items requested.
            unit_cost: Cost per item.
            item_name: Name for error message.

        Returns:
            Tuple of (actual_count, total_cost).

        Raises:
            InsufficientFundsError: If cannot afford any items.
        """
        total_cost = count * unit_cost

        if self._fund < total_cost:
            affordable_count = int(self._fund // unit_cost)
            if affordable_count == 0:
                raise InsufficientFundsError(
                    f"Need ${total_cost:.2f} for {count} {item_name}, have ${self._fund}"
                )
            return affordable_count, int(affordable_count * unit_cost)

        return count, int(total_cost)

    def remove_funds_for_wire(self, count: int) -> int:
        """Remove funds for wire purchase. Returns actual count purchased."""
        actual_count, total_cost = self._process_purchase(
            count, self._wire_cost, "spools"
        )
        self._fund -= total_cost
        return actual_count

    def remove_funds_for_autoclipper(self, count: int) -> int:
        """Remove funds for autoclipper purchase. Returns actual count purchased."""
        actual_count, total_cost = self._process_purchase(
            count, self.autoclipper_cost, "autoclippers"
        )
        self._fund -= total_cost
        self._autoclipper_count += actual_count
        return actual_count

    async def start(self) -> None:
        """Start the purchasing module and subscribe to events."""
        await self._subscribe_to_events()

    async def _subscribe_to_events(self) -> None:
        """Subscribe to all relevant events."""
        await self._event_bus.subscribe(
            EventName.PLAN_PHASE_STARTED, self._on_plan_phase_started
        )
        await self._event_bus.subscribe(EventName.BUY_WIRE, self._on_buy_wire)
        await self._event_bus.subscribe(
            EventName.BUY_AUTOCLIPPER, self._on_buy_autoclipper
        )
        await self._event_bus.subscribe(
            EventName.ACTION_PHASE_STARTED, self._on_action_phase_started
        )
        await self._event_bus.subscribe(EventName.CLIPS_SOLD, self._on_clips_sold)

    def _on_plan_phase_started(self, event: Event) -> None:
        """Report current state when planning phase starts."""
        import asyncio

        # Spawn task because event handlers must be synchronous (EventBus listener constraint)
        asyncio.create_task(self._report_state(event))

    async def _report_state(self, event: Event) -> None:
        """Report current state to event bus."""
        self._current_turn = event.turn
        self._pending_wire_purchases.clear()
        self._pending_autoclipper_purchases.clear()
        await self._event_bus.publish(
            EventName.PURCHASING_STATE_REPORTED,
            PurchasingStateReportedPayload(
                fund=self._fund,
                wire_cost=self._wire_cost,
                autoclipper_cost=self.autoclipper_cost,
            ),
            turn=event.turn,
        )

    def _on_buy_wire(self, event: Event) -> None:
        """Queue a wire purchase request."""
        # Reject stale events from previous turns (race condition protection)
        if event.turn != self._current_turn:
            return
        payload = BuyWirePayload(**event.payload.model_dump())
        self._pending_wire_purchases.append(payload.count)

    def _on_buy_autoclipper(self, event: Event) -> None:
        """Queue an autoclipper purchase request."""
        # Reject stale events from previous turns (race condition protection)
        if event.turn != self._current_turn:
            return
        payload = BuyAutoclipperPayload(**event.payload.model_dump())
        self._pending_autoclipper_purchases.append(payload.count)

    def _on_action_phase_started(self, event: Event) -> None:
        """Process queued purchase requests during action phase."""
        import asyncio

        # Spawn task because event handlers must be synchronous (EventBus listener constraint)
        asyncio.create_task(self._process_action_phase(event))

    async def _process_action_phase(self, event: Event) -> None:
        """Process queued purchase requests during action phase."""
        wire_purchased = False

        for count in self._pending_wire_purchases:
            try:
                actual_count = self.remove_funds_for_wire(count)
                wire_purchased = True
                await self._event_bus.publish(
                    EventName.WIRE_PURCHASE_APPROVED,
                    WirePurchaseApprovedPayload(count=actual_count),
                    turn=event.turn,
                )
            except InsufficientFundsError:
                pass

        # Wire cost drift: increases after purchases, decays when idle (market pressure)
        if wire_purchased:
            self._wire_cost += WireCost.WIRE_COST_INCREASE
        else:
            self._wire_cost = max(
                WireCost.WIRE_COST_MIN,
                self._wire_cost - WireCost.WIRE_COST_DECAY,
            )

        # Apply random noise each turn (market fluctuation)
        noise = random.gauss(0, WireCost.WIRE_NOISE_STD_DEV)
        self._wire_cost = max(WireCost.WIRE_COST_MIN, self._wire_cost + noise)

        for count in self._pending_autoclipper_purchases:
            try:
                actual_count = self.remove_funds_for_autoclipper(count)
                await self._event_bus.publish(
                    EventName.AUTOCLIPPER_PURCHASE_APPROVED,
                    AutoclipperPurchaseApprovedPayload(count=actual_count),
                    turn=event.turn,
                )
            except InsufficientFundsError:
                pass

        await self._event_bus.publish(
            EventName.PURCHASING_ACTION_COMPLETED,
            EmptyPayload(),
            turn=event.turn,
        )

    def _on_clips_sold(self, event: Event) -> None:
        """Add revenue from clip sales."""
        payload = ClipsSoldPayload(**event.payload.model_dump())
        self.add_funds(payload.revenue)
