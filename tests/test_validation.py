"""Unit tests for shared validation tools."""

import pytest

from src.events.schemas import ValidationError
from src.utils.validation import ExternalAction, validate_action


class TestTurnValidation:
    """Tests for turn validation."""

    def test_turn_zero_raises_error(self):
        """Turn 0 is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            validate_action(ExternalAction.BUY_WIRE, {"count": 1}, turn=0)

        assert exc_info.value.code == 4001

    def test_negative_turn_raises_error(self):
        """Negative turn is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            validate_action(ExternalAction.BUY_WIRE, {"count": 1}, turn=-1)

        assert exc_info.value.code == 4001


class TestBuyWireValidation:
    """Tests for buy_wire action validation."""

    def test_count_zero_raises_error(self):
        """Count of 0 is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            validate_action(ExternalAction.BUY_WIRE, {"count": 0}, turn=1)

        assert exc_info.value.code == 4001

    def test_negative_count_raises_error(self):
        """Negative count is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            validate_action(ExternalAction.BUY_WIRE, {"count": -10}, turn=1)

        assert exc_info.value.code == 4001

    def test_large_count_succeeds(self):
        """Large positive count is valid."""
        validate_action(ExternalAction.BUY_WIRE, {"count": 1000000}, turn=1)

    def test_missing_count_raises_key_error(self):
        """Missing 'count' key raises KeyError."""
        with pytest.raises(KeyError):
            validate_action(ExternalAction.BUY_WIRE, {}, turn=1)


class TestBuyAutoclipperValidation:
    """Tests for buy_autoclipper action validation."""

    def test_count_zero_raises_error(self):
        """Count of 0 is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            validate_action(ExternalAction.BUY_AUTOCLIPPER, {"count": 0}, turn=1)

        assert exc_info.value.code == 4001

    def test_negative_count_raises_error(self):
        """Negative count is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            validate_action(ExternalAction.BUY_AUTOCLIPPER, {"count": -5}, turn=1)

        assert exc_info.value.code == 4001

    def test_large_count_succeeds(self):
        """Large positive count is valid."""
        validate_action(ExternalAction.BUY_AUTOCLIPPER, {"count": 500}, turn=1)

    def test_missing_count_raises_key_error(self):
        """Missing 'count' key raises KeyError."""
        with pytest.raises(KeyError):
            validate_action(ExternalAction.BUY_AUTOCLIPPER, {}, turn=1)


class TestSetPriceValidation:
    """Tests for set_price action validation."""

    def test_price_zero_raises_error(self):
        """Price of 0 is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            validate_action(ExternalAction.SET_PRICE, {"price": 0.0}, turn=1)

        assert exc_info.value.code == 4001

    def test_negative_price_raises_error(self):
        """Negative price is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            validate_action(ExternalAction.SET_PRICE, {"price": -0.05}, turn=1)

        assert exc_info.value.code == 4001

    def test_large_price_succeeds(self):
        """Large prices are valid."""
        validate_action(ExternalAction.SET_PRICE, {"price": 999.99}, turn=1)

    def test_missing_price_raises_key_error(self):
        """Missing 'price' key raises KeyError."""
        with pytest.raises(KeyError):
            validate_action(ExternalAction.SET_PRICE, {}, turn=1)
