"""Validation logic for external agent actions."""

from enum import Enum

from src.events.schemas import ValidationError


class ExternalAction(str, Enum):
    """External actions that can be validated."""

    BUY_WIRE = "buy_wire"
    BUY_AUTOCLIPPER = "buy_autoclipper"
    SET_PRICE = "set_price"


def validate_action(action: ExternalAction, payload: dict, turn: int) -> None:
    """Validate external action payload and turn.

    Args:
        action: The action to validate.
        payload: The payload to validate.
        turn: Current turn number.

    Raises:
        ValidationError: If validation fails.
    """
    if turn < 1:
        raise ValidationError("turn must be >= 1")

    match action:
        case ExternalAction.BUY_WIRE:
            _validate_buy_wire(payload)
        case ExternalAction.BUY_AUTOCLIPPER:
            _validate_buy_autoclipper(payload)
        case ExternalAction.SET_PRICE:
            _validate_set_price(payload)


def _validate_buy_wire(payload: dict) -> None:
    """Validate buy_wire action payload."""
    count = payload["count"]
    if count <= 0:
        raise ValidationError("'count' must be a positive integer")


def _validate_buy_autoclipper(payload: dict) -> None:
    """Validate buy_autoclipper action payload."""
    count = payload["count"]
    if count <= 0:
        raise ValidationError("'count' must be a positive integer")


def _validate_set_price(payload: dict) -> None:
    """Validate set_price action payload."""
    price = payload["price"]
    if price <= 0:
        raise ValidationError("'price' must be a positive number")
