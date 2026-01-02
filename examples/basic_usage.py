"""Basic usage example of the trading simulator."""

import sys
sys.path.insert(0, '../src')

from trading_simulator import (
    TradingSimulator,
    OrderType,
    OrderSide,
    PnLMode,
    Candle,
)


def main():
    # Initialize simulator with $10,000, 0.1% fees
    simulator = TradingSimulator(
        initial_balance=10000,
        pnl_mode=PnLMode.FIAT,
        fee_rate=0.001,  # 0.1%
    )

    print("=== Trading Simulator Example ===\n")
    print(f"Initial balance: ${simulator.balance:.2f}\n")

    # 1. Send initial market data
    candle1 = Candle(open=100, high=101, low=99, close=100, volume=1000)
    simulator.update_market(candle1)
    print(f"Market update: Price = ${candle1.close}")

    # 2. Place a market buy order
    print("\n--- Opening Long Position ---")
    order = simulator.place_order(
        order_type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=10.0,
        stop_loss=95.0,      # Stop loss at $95
        take_profit=110.0,   # Take profit at $110
    )
    print(f"Placed market BUY order: {order.quantity} units @ ${order.filled_price}")
    print(f"Stop Loss: ${order.stop_loss}, Take Profit: ${order.take_profit}")

    # Check position
    position = simulator.get_position()
    print(f"Position: {position.quantity} units @ avg price ${position.average_price:.2f}")
    print(f"Pending orders (SL/TP): {len(simulator.get_pending_orders())}")

    # 3. Market moves up
    print("\n--- Market Movement ---")
    candle2 = Candle(open=102, high=105, low=101, close=104, volume=1200)
    simulator.update_market(candle2)
    print(f"Price moved to: ${candle2.close}")

    pnl = simulator.get_pnl()
    print(f"Unrealized PnL: ${pnl['unrealized']:.2f}")
    print(f"Total PnL: ${pnl['total']:.2f}")

    # 4. Market continues up and hits take profit
    print("\n--- Take Profit Hit ---")
    candle3 = Candle(open=108, high=111, low=107, close=110, volume=1500)
    trades = simulator.update_market(candle3)
    print(f"Price reached: ${candle3.close}")
    print(f"Trades executed: {len(trades)}")

    if trades:
        for trade in trades:
            print(f"  - {trade.side.name} {trade.quantity} @ ${trade.price:.2f} (fees: ${trade.fees:.2f})")

    # Check final state
    position = simulator.get_position()
    pnl = simulator.get_pnl()
    state = simulator.get_state()

    print("\n--- Final State ---")
    print(f"Position: {'FLAT' if position.is_flat else f'{position.quantity} units'}")
    print(f"Realized PnL: ${pnl['realized']:.2f}")
    print(f"Total Fees: ${pnl['fees']:.2f}")
    print(f"Net PnL: ${pnl['net']:.2f}")
    print(f"Final Balance: ${simulator.balance:.2f}")
    print(f"Equity: ${state['equity']:.2f}")

    # 5. Demonstrate limit order
    print("\n\n=== Limit Order Example ===\n")
    simulator.reset()
    print("Simulator reset")

    # Set market price
    candle4 = Candle(open=100, high=101, low=99, close=100, volume=1000)
    simulator.update_market(candle4)
    print(f"Current price: ${candle4.close}")

    # Place buy limit below market
    print("\n--- Placing Limit Order ---")
    limit_order = simulator.place_order(
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=5.0,
        price=98.0,
    )
    print(f"Placed LIMIT BUY order: {limit_order.quantity} units @ ${limit_order.price}")
    print(f"Order status: {limit_order.status.name}")
    print(f"Pending orders: {len(simulator.get_pending_orders())}")

    # Price doesn't reach limit yet
    candle5 = Candle(open=100, high=101, low=99, close=100.5, volume=1000)
    trades = simulator.update_market(candle5)
    print(f"\nPrice: ${candle5.close} (limit not hit)")
    print(f"Trades executed: {len(trades)}")
    print(f"Pending orders: {len(simulator.get_pending_orders())}")

    # Price drops and hits limit
    candle6 = Candle(open=99, high=99, low=97, close=98, volume=1000)
    trades = simulator.update_market(candle6)
    print(f"\nPrice: ${candle6.close} (limit hit!)")
    print(f"Trades executed: {len(trades)}")
    print(f"Pending orders: {len(simulator.get_pending_orders())}")

    position = simulator.get_position()
    print(f"Position: {position.quantity} units @ ${position.average_price:.2f}")

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()
