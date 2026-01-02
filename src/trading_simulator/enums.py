"""Enumerations for trading simulator."""

from enum import Enum, auto


class OrderType(Enum):
    """Types of orders supported by the simulator."""
    MARKET = auto()
    LIMIT = auto()
    STOP_LOSS = auto()
    TAKE_PROFIT = auto()


class OrderSide(Enum):
    """Direction of the order."""
    BUY = auto()
    SELL = auto()


class OrderStatus(Enum):
    """Status of an order."""
    PENDING = auto()      # Order placed but not executed
    FILLED = auto()       # Order executed
    CANCELLED = auto()    # Order cancelled
    REJECTED = auto()     # Order rejected (insufficient balance, etc.)


class PnLMode(Enum):
    """Mode for calculating Profit and Loss."""
    FIAT = auto()      # Standard currency (USD, EUR, etc.)
    TICKS = auto()     # Futures contracts (price * tick_size * quantity)
    PIPS = auto()      # Forex (price difference in pips)
    POINTS = auto()    # Index points
