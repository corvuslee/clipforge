"""Game constants and initial state values."""


class InitialState:
    """Initial state values for game startup."""

    FUND: int = 0
    WIRE_INCH: int = 150
    WIRE_COST: float = 20.0
    AUTOCLIPPER_COST: float = 50.0
    CLIP_PRICE: float = 0.05
    AUTO_CLIPPERS: int = 1
    UNSOLD_CLIPS: int = 0
    TOTAL_CLIPS: int = 0


class WireCost:
    """Wire cost function constants."""

    WIRE_COST_MIN: float = 15.0
    WIRE_COST_INCREASE: float = 0.50
    WIRE_COST_DECAY: float = 0.25
    WIRE_NOISE_STD_DEV: float = 1.0
    WIRE_INCH_PER_SPOOL: int = 1000


class AutoclipperCost:
    """Autoclipper cost function constants."""

    AUTOCLIPPER_BASE_COST: float = 50.0
    AUTOCLIPPER_GROWTH_RATE: float = 1.004


class Production:
    """Production function constants."""

    CLIPS_PER_AUTOCLIPPER: int = 30
    WIRE_PER_CLIP: int = 1


class Demand:
    """Demand function constants."""

    BASE_DEMAND: float = 0.38
    PRICE_FACTOR_PEAK: float = 2.0
    PRICE_FACTOR_SIGMA: float = 0.04
    AUTOCLIPPER_FACTOR: float = 0.10
    INVENTORY_THRESHOLD_FACTOR: float = 2.0
    DEMAND_NOISE_STD_DEV: float = 0.02
