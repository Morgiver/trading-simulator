# Trading Simulator

A comprehensive trading simulation library for reinforcement learning and backtesting.

## Features

- Position management (long/short)
- Multiple PnL calculation modes (Fiat, Ticks, Pips, Points)
- Realized and unrealized PnL tracking
- Order types: Market, Limit, Stop Loss, Take Profit
- Transaction fees support
- Trade history tracking
- In-memory simulation (fast)

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from trading_simulator import TradingSimulator, OrderType, OrderSide, PnLMode, Candle

# Initialize simulator
simulator = TradingSimulator(
    initial_balance=10000,
    pnl_mode=PnLMode.FIAT,
    fee_rate=0.001  # 0.1%
)

# Send market data
candle = Candle(open=100, high=101, low=99, close=100.5, volume=1000)
simulator.update_market(candle)

# Place a market order
order = simulator.place_order(
    order_type=OrderType.MARKET,
    side=OrderSide.BUY,
    quantity=1.0,
    price=None  # Market price
)

# Get current PnL
pnl_info = simulator.get_pnl()
print(f"Unrealized PnL: {pnl_info['unrealized']}")
print(f"Realized PnL: {pnl_info['realized']}")

# Get position
position = simulator.get_position()
print(f"Position: {position.quantity} @ {position.average_price}")
```

## API Reference

### TradingSimulator

Main simulator class.

**Methods:**
- `place_order(order_type, side, quantity, price=None, stop_loss=None, take_profit=None)` - Place an order
- `update_market(candle)` - Update with new market data
- `get_pnl()` - Get realized and unrealized PnL
- `get_position()` - Get current position
- `get_trade_history()` - Get all executed trades
- `get_pending_orders()` - Get pending limit/stop orders

## PnL Modes

- **FIAT**: Standard currency (USD, EUR, etc.)
- **TICKS**: Futures contracts (price * tick_size * quantity)
- **PIPS**: Forex (price difference in pips)
- **POINTS**: Index points

## License

MIT
