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


MODULES = {"ledger", "inventory", "factory", "market"}


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
        await self._subscribe_to_events()
        await self._start_planning_phase()

    async def _subscribe_to_events(self) -> None:
        """Subscribe to all relevant events."""
        await self._event_bus.subscribe(
            EventName.PLAN_PHASE_COMPLETED, self._on_plan_phase_completed
        )
        await self._event_bus.subscribe(
            EventName.LEDGER_STATE_REPORTED, self._on_ledger_state_reported
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
            EventName.LEDGER_ACTION_COMPLETED, self._on_ledger_action_completed
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

    async def _start_planning_phase(self) -> None:
        """Start the planning phase for current turn.

        No phase validation needed: only called internally from start() and _complete_turn(),
        which guarantee correct state.
        """
        self._turn_counter += 1
        self._current_phase = Phase.PLANNING
        self._pending_state_reports = MODULES.copy()

        await self._event_bus.publish(
            EventName.PLAN_PHASE_STARTED, EmptyPayload(), turn=self._turn_counter
        )

    async def _start_action_phase(self) -> None:
        """Start the action phase for current turn."""
        if self._current_phase != Phase.PLANNING:
            phase_name = self._current_phase.value if self._current_phase else "None"
            raise TurnSequenceError(f"Cannot start action phase from {phase_name}")

        self._current_phase = Phase.ACTION
        self._pending_action_completions = MODULES.copy()

        await self._event_bus.publish(
            EventName.ACTION_PHASE_STARTED, EmptyPayload(), turn=self._turn_counter
        )

    async def _complete_turn(self) -> None:
        """Complete the current turn and start the next."""
        if self._current_phase != Phase.ACTION:
            phase_name = self._current_phase.value if self._current_phase else "None"
            raise TurnSequenceError(f"Cannot complete turn from {phase_name}")

        await self._event_bus.publish(
            EventName.ACTION_PHASE_COMPLETED, EmptyPayload(), turn=self._turn_counter
        )

        await self._start_planning_phase()

    def _handle_state_report(self, module: str, event: Event) -> None:
        """Process a state report from a module."""
        # Reject stale events from previous turns
        if event.turn < self._turn_counter:
            return

        # Track module reports and open planning window when all 4 have reported
        if module in self._pending_state_reports:
            self._pending_state_reports.discard(module)

            # All modules reported?
            if not self._pending_state_reports:
                asyncio.create_task(self._open_planning_window())

    def _on_ledger_state_reported(self, event: Event) -> None:
        """Handle ledger state report."""
        self._handle_state_report("ledger", event)

    def _on_inventory_state_reported(self, event: Event) -> None:
        """Handle inventory state report."""
        self._handle_state_report("inventory", event)

    def _on_factory_state_reported(self, event: Event) -> None:
        """Handle factory state report."""
        self._handle_state_report("factory", event)

    def _on_market_state_reported(self, event: Event) -> None:
        """Handle market state report."""
        self._handle_state_report("market", event)

    async def _open_planning_window(self) -> None:
        """Open planning window to external agents."""
        await self._event_bus.publish(
            EventName.PLANNING_WINDOW_OPENED, EmptyPayload(), turn=self._turn_counter
        )

    def _on_plan_phase_completed(self, event: Event) -> None:
        """Handle plan_phase_completed from external agent."""
        if event.turn != self._turn_counter:
            return

        asyncio.create_task(self._start_action_phase())

    def _handle_action_completed(self, module: str, event: Event) -> None:
        """Process an action completion from a module."""
        # Reject stale events from previous turns
        if event.turn < self._turn_counter:
            return

        # Track module completions and end turn when all 4 have completed
        if module in self._pending_action_completions:
            self._pending_action_completions.discard(module)

            # All modules completed?
            if not self._pending_action_completions:
                asyncio.create_task(self._complete_turn())

    def _on_ledger_action_completed(self, event: Event) -> None:
        """Handle ledger action completion."""
        self._handle_action_completed("ledger", event)

    def _on_inventory_action_completed(self, event: Event) -> None:
        """Handle inventory action completion."""
        self._handle_action_completed("inventory", event)

    def _on_factory_action_completed(self, event: Event) -> None:
        """Handle factory action completion."""
        self._handle_action_completed("factory", event)

    def _on_market_action_completed(self, event: Event) -> None:
        """Handle market action completion."""
        self._handle_action_completed("market", event)
