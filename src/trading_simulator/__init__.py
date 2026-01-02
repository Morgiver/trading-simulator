"""Trading Simulator - A comprehensive trading simulation library."""

from .simulator import TradingSimulator
from .enums import OrderType, OrderSide, PnLMode, OrderStatus
from .models import Order, Position, Trade, Candle

__version__ = "0.1.0"
__all__ = [
    "TradingSimulator",
    "OrderType",
    "OrderSide",
    "PnLMode",
    "OrderStatus",
    "Order",
    "Position",
    "Trade",
    "Candle",
]
