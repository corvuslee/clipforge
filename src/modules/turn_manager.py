"""Turn Manager module for orchestrating game phases."""

import asyncio
from enum import Enum

from src.events.bus import EventBus
from src.events.schemas import (
    EmptyPayload,
    Event,
    EventName,
    TurnSequenceError,
)


class Phase(str, Enum):
    """Game phases."""

    PLANNING = "planning"
    ACTION = "action"


MODULES = {"purchasing", "inventory", "factory", "market"}


class TurnManager:
    """Centralizes turn sequencing and time-step control."""

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._turn_counter: int = 0
        self._current_phase: Phase | None = None
        self._pending_state_reports: set[str] = set()
        self._pending_action_completions: set[str] = set()
        self._running: bool = False

    @property
    def turn_counter(self) -> int:
        """Current turn number."""
        return self._turn_counter

    @property
    def current_phase(self) -> Phase | None:
        """Current game phase. None before start()."""
        return self._current_phase

    async def start(self) -> None:
        """Start the turn manager and begin turn 1."""
        if self._running:
            return

        self._running = True
        # State transition before first await to prevent race conditions
        self._turn_counter = 1
        self._current_phase = Phase.PLANNING
        self._pending_state_reports = MODULES.copy()

        await self._subscribe_to_events()
        await self._event_bus.publish(
            EventName.PLAN_PHASE_STARTED, EmptyPayload(), turn=self._turn_counter
        )

    async def _subscribe_to_events(self) -> None:
        """Subscribe to all relevant events."""
        await self._event_bus.subscribe(
            EventName.PLAN_PHASE_COMPLETED, self._on_plan_phase_completed
        )
        await self._event_bus.subscribe(
            EventName.PURCHASING_STATE_REPORTED, self._on_purchasing_state_reported
        )
        await self._event_bus.subscribe(
            EventName.INVENTORY_STATE_REPORTED, self._on_inventory_state_reported
        )
        await self._event_bus.subscribe(
            EventName.FACTORY_STATE_REPORTED, self._on_factory_state_reported
        )
        await self._event_bus.subscribe(
            EventName.MARKET_STATE_REPORTED, self._on_market_state_reported
        )
        await self._event_bus.subscribe(
            EventName.PURCHASING_ACTION_COMPLETED, self._on_purchasing_action_completed
        )
        await self._event_bus.subscribe(
            EventName.INVENTORY_ACTION_COMPLETED, self._on_inventory_action_completed
        )
        await self._event_bus.subscribe(
            EventName.FACTORY_ACTION_COMPLETED, self._on_factory_action_completed
        )
        await self._event_bus.subscribe(
            EventName.MARKET_ACTION_COMPLETED, self._on_market_action_completed
        )

    def _on_plan_phase_completed(self, event: Event) -> None:
        """Handle plan_phase_completed from external agent."""
        if event.turn != self._turn_counter:
            return

        # Defensive check: must be in PLANNING phase
        if self._current_phase != Phase.PLANNING:
            raise TurnSequenceError(
                f"Cannot start action phase from {self._current_phase}"
            )

        # Transition to ACTION phase synchronously
        self._current_phase = Phase.ACTION
        self._pending_action_completions = MODULES.copy()
        asyncio.create_task(
            self._event_bus.publish(
                EventName.ACTION_PHASE_STARTED, EmptyPayload(), turn=self._turn_counter
            )
        )

    def _track_state_report(self, module: str, event: Event) -> None:
        """Track a state report from a module."""
        # Reject stale events from previous turns
        if event.turn < self._turn_counter:
            return

        if module in self._pending_state_reports:
            self._pending_state_reports.discard(module)

            # All modules reported - open planning window
            if not self._pending_state_reports:
                # Defensive check: must be in PLANNING phase
                if self._current_phase != Phase.PLANNING:
                    raise TurnSequenceError(
                        f"Cannot open planning window from {self._current_phase}"
                    )
                asyncio.create_task(
                    self._event_bus.publish(
                        EventName.PLANNING_WINDOW_OPENED,
                        EmptyPayload(),
                        turn=self._turn_counter,
                    )
                )

    def _on_purchasing_state_reported(self, event: Event) -> None:
        """Handle purchasing state report."""
        self._track_state_report("purchasing", event)

    def _on_inventory_state_reported(self, event: Event) -> None:
        """Handle inventory state report."""
        self._track_state_report("inventory", event)

    def _on_factory_state_reported(self, event: Event) -> None:
        """Handle factory state report."""
        self._track_state_report("factory", event)

    def _on_market_state_reported(self, event: Event) -> None:
        """Handle market state report."""
        self._track_state_report("market", event)

    def _track_action_completion(self, module: str, event: Event) -> None:
        """Track an action completion from a module."""
        # Reject stale events from previous turns
        if event.turn < self._turn_counter:
            return

        # Track module completions and end turn when all 4 have completed
        if module in self._pending_action_completions:
            self._pending_action_completions.discard(module)

            # All modules completed - transition to next turn
            if not self._pending_action_completions:
                # Defensive check: must be in ACTION phase
                if self._current_phase != Phase.ACTION:
                    raise TurnSequenceError(
                        f"Cannot complete turn from {self._current_phase}"
                    )
                self._turn_counter += 1
                self._current_phase = Phase.PLANNING
                self._pending_state_reports = MODULES.copy()
                asyncio.create_task(
                    self._event_bus.publish(
                        EventName.ACTION_PHASE_COMPLETED,
                        EmptyPayload(),
                        turn=self._turn_counter - 1,
                    )
                )
                asyncio.create_task(
                    self._event_bus.publish(
                        EventName.PLAN_PHASE_STARTED,
                        EmptyPayload(),
                        turn=self._turn_counter,
                    )
                )

    def _on_purchasing_action_completed(self, event: Event) -> None:
        """Handle purchasing action completion."""
        self._track_action_completion("purchasing", event)

    def _on_inventory_action_completed(self, event: Event) -> None:
        """Handle inventory action completion."""
        self._track_action_completion("inventory", event)

    def _on_factory_action_completed(self, event: Event) -> None:
        """Handle factory action completion."""
        self._track_action_completion("factory", event)

    def _on_market_action_completed(self, event: Event) -> None:
        """Handle market action completion."""
        self._track_action_completion("market", event)
