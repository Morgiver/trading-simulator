"""Data models for trading simulator."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from .enums import OrderType, OrderSide, OrderStatus


@dataclass
class Order:
    """Represents a trading order."""
    order_type: OrderType
    side: OrderSide
    quantity: float
    price: Optional[float] = None  # None for market orders
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    order_id: Optional[str] = None
    created_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    fees: float = 0.0

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.order_id is None:
            self.order_id = f"{self.created_at.timestamp()}_{id(self)}"


@dataclass
class Trade:
    """Represents an executed trade."""
    side: OrderSide
    quantity: float
    price: float
    fees: float
    timestamp: datetime
    trade_id: Optional[str] = None
    pnl: float = 0.0  # Realized PnL for closing trades

    def __post_init__(self):
        if self.trade_id is None:
            self.trade_id = f"{self.timestamp.timestamp()}_{id(self)}"


@dataclass
class Position:
    """Represents the current position."""
    quantity: float = 0.0  # Positive = long, Negative = short, 0 = no position
    average_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_fees: float = 0.0

    @property
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.quantity > 0

    @property
    def is_short(self) -> bool:
        """Check if position is short."""
        return self.quantity < 0

    @property
    def is_flat(self) -> bool:
        """Check if there's no position."""
        return self.quantity == 0

    @property
    def side(self) -> Optional[OrderSide]:
        """Get the side of the position."""
        if self.is_long:
            return OrderSide.BUY
        elif self.is_short:
            return OrderSide.SELL
        return None
