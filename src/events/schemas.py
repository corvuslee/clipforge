"""Event schemas and type definitions for the event bus."""

from enum import Enum
from typing import Union

from pydantic import BaseModel


# =============================================================================
# Errors
# =============================================================================


class EventBusError(Exception):
    """Base error for event bus operations."""

    def __init__(self, code: int = 5601, message: str = "Event bus operation failed"):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class PublishError(EventBusError):
    """Failed to publish event."""

    def __init__(self, message: str = "Failed to publish event"):
        super().__init__(code=5602, message=message)


class SubscribeError(EventBusError):
    """Failed to subscribe to event."""

    def __init__(self, message: str = "Failed to subscribe to event"):
        super().__init__(code=5603, message=message)


class TurnSequenceError(Exception):
    """Invalid turn transition."""

    def __init__(self, message: str = "Invalid turn transition"):
        self.code = 5101
        self.message = message
        super().__init__(f"[{self.code}] {message}")


class InsufficientFundsError(Exception):
    """Insufficient funds for requested operation."""

    def __init__(self, message: str = "Insufficient funds for requested operation"):
        self.code = 4101
        self.message = message
        super().__init__(f"[{self.code}] {message}")


class InsufficientResourcesError(Exception):
    """Not enough resources for requested operation."""

    def __init__(self, message: str = "Not enough resources for requested operation"):
        self.code = 4201
        self.message = message
        super().__init__(f"[{self.code}] {message}")


class InsufficientCapacityError(Exception):
    """Not enough autoclippers to remove."""

    def __init__(self, message: str = "Not enough autoclippers to remove"):
        self.code = 4301
        self.message = message
        super().__init__(f"[{self.code}] {message}")


class InvalidPriceError(Exception):
    """Price must be a positive number."""

    def __init__(self, message: str = "Price must be a positive number"):
        self.code = 4401
        self.message = message
        super().__init__(f"[{self.code}] {message}")


class ValidationError(Exception):
    """Action validation failed."""

    def __init__(self, message: str = "Action validation failed"):
        self.code = 4001
        self.message = message
        super().__init__(f"[{self.code}] {message}")


# =============================================================================
# Event Names
# =============================================================================


class EventName(str, Enum):
    """All event names in the system."""

    # Turn Manager events
    PLAN_PHASE_STARTED = "plan_phase_started"
    PLANNING_WINDOW_OPENED = "planning_window_opened"
    ACTION_PHASE_STARTED = "action_phase_started"
    ACTION_PHASE_COMPLETED = "action_phase_completed"

    # External Agent actions
    BUY_WIRE = "buy_wire"
    BUY_AUTOCLIPPER = "buy_autoclipper"
    SET_PRICE = "set_price"
    PLAN_PHASE_COMPLETED = "plan_phase_completed"

    # Ledger events
    LEDGER_STATE_REPORTED = "ledger_state_reported"
    WIRE_PURCHASE_APPROVED = "wire_purchase_approved"
    AUTOCLIPPER_PURCHASE_APPROVED = "autoclipper_purchase_approved"
    LEDGER_ACTION_COMPLETED = "ledger_action_completed"

    # Inventory events
    INVENTORY_STATE_REPORTED = "inventory_state_reported"
    INVENTORY_ACTION_COMPLETED = "inventory_action_completed"

    # Factory events
    FACTORY_STATE_REPORTED = "factory_state_reported"
    WIRE_CONSUMED = "wire_consumed"
    CLIPS_PRODUCED = "clips_produced"
    FACTORY_ACTION_COMPLETED = "factory_action_completed"

    # Market events
    MARKET_STATE_REPORTED = "market_state_reported"
    CLIPS_SOLD = "clips_sold"
    MARKET_ACTION_COMPLETED = "market_action_completed"


# =============================================================================
# Event Payloads
# =============================================================================


class EmptyPayload(BaseModel):
    """Empty payload for events with no data."""

    pass


class BuyWirePayload(BaseModel):
    """Payload for buy_wire event."""

    count: int


class BuyAutoclipperPayload(BaseModel):
    """Payload for buy_autoclipper event."""

    count: int


class SetPricePayload(BaseModel):
    """Payload for set_price event."""

    price: float


class LedgerStateReportedPayload(BaseModel):
    """Payload for ledger_state_reported event."""

    fund: int


class WirePurchaseApprovedPayload(BaseModel):
    """Payload for wire_purchase_approved event."""

    count: int


class AutoclipperPurchaseApprovedPayload(BaseModel):
    """Payload for autoclipper_purchase_approved event."""

    count: int


class InventoryStateReportedPayload(BaseModel):
    """Payload for inventory_state_reported event."""

    wire: int
    unsold_clips: int
    total_clips: int


class FactoryStateReportedPayload(BaseModel):
    """Payload for factory_state_reported event."""

    auto_clippers: int


class WireConsumedPayload(BaseModel):
    """Payload for wire_consumed event."""

    count: int


class ClipsProducedPayload(BaseModel):
    """Payload for clips_produced event."""

    count: int


class MarketStateReportedPayload(BaseModel):
    """Payload for market_state_reported event."""

    price: float


class ClipsSoldPayload(BaseModel):
    """Payload for clips_sold event."""

    clips: int
    revenue: int


# =============================================================================
# Payload Union
# =============================================================================


Payload = Union[
    BuyWirePayload,
    BuyAutoclipperPayload,
    SetPricePayload,
    LedgerStateReportedPayload,
    WirePurchaseApprovedPayload,
    AutoclipperPurchaseApprovedPayload,
    InventoryStateReportedPayload,
    FactoryStateReportedPayload,
    WireConsumedPayload,
    ClipsProducedPayload,
    MarketStateReportedPayload,
    ClipsSoldPayload,
    EmptyPayload,
]


# =============================================================================
# Event
# =============================================================================


class Event(BaseModel):
    """Represents an event in the system."""

    name: EventName
    payload: Payload
    turn: int
