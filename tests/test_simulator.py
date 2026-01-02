"""Tests for the trading simulator."""

import pytest
from datetime import datetime
from trading_simulator import (
    TradingSimulator,
    OrderType,
    OrderSide,
    PnLMode,
    OrderStatus,
    Candle,
)




def create_candle(open_price, high_price, low_price, close_price, volume=1000, date=None):
    """Helper function to create a Candle with trading-frame format."""
    if date is None:
        date = datetime.now()
    return Candle(
        date=date,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume
    )

class TestTradingSimulator:
    """Test suite for TradingSimulator."""

    def test_initialization(self):
        """Test simulator initialization."""
        sim = TradingSimulator(
            initial_balance=10000,
            pnl_mode=PnLMode.FIAT,
            fee_rate=0.001,
        )
        assert sim.balance == 10000
        assert sim.pnl_mode == PnLMode.FIAT

    def test_market_order_buy(self):
        """Test placing a market buy order."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.001)

        # Update market first
        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)

        # Place market buy
        order = sim.place_order(
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=1.0,
        )

        # Check position
        position = sim.get_position()
        assert position.quantity == 1.0
        assert position.average_price == 100.0

        # Check fees were deducted
        expected_fee = 100 * 1.0 * 0.001
        assert sim.balance == 10000 - expected_fee

    def test_market_order_sell(self):
        """Test placing a market sell order (short)."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.001)

        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)

        # Place market sell (short)
        sim.place_order(
            order_type=OrderType.MARKET,
            side=OrderSide.SELL,
            quantity=1.0,
        )

        position = sim.get_position()
        assert position.quantity == -1.0
        assert position.average_price == 100.0
        assert position.is_short

    def test_close_position_with_profit(self):
        """Test closing a position with profit."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.001)

        # Open long position
        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 1.0)

        # Price goes up
        candle2 = create_candle(105, 106, 104, 105, 1000)
        sim.update_market(candle2)

        # Close position
        sim.place_order(OrderType.MARKET, OrderSide.SELL, 1.0)

        position = sim.get_position()
        assert position.is_flat

        pnl = sim.get_pnl()
        # Profit: 105 - 100 = 5
        # Fees: (100 * 1 * 0.001) + (105 * 1 * 0.001) = 0.205
        # Net: 5 - 0.205 = 4.795
        assert pnl["realized"] == 5.0 - (105 * 1 * 0.001)  # Realized PnL minus closing fee
        assert pnl["unrealized"] == 0.0

    def test_unrealized_pnl(self):
        """Test unrealized PnL calculation."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        # Open long position
        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 1.0)

        # Price goes up but position not closed
        candle2 = create_candle(105, 106, 104, 105, 1000)
        sim.update_market(candle2)

        pnl = sim.get_pnl()
        assert pnl["unrealized"] == 5.0  # 105 - 100
        assert pnl["realized"] == 0.0

    def test_limit_order_execution(self):
        """Test limit order execution."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        # Set initial market price
        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)

        # Place buy limit below current price
        sim.place_order(
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=1.0,
            price=98.0,
        )

        # Limit order should be pending
        assert len(sim.get_pending_orders()) == 1

        # Price drops to trigger limit
        candle2 = create_candle(99, 99, 97, 98, 1000)
        trades = sim.update_market(candle2)

        # Order should be executed
        assert len(trades) == 1
        assert len(sim.get_pending_orders()) == 0
        position = sim.get_position()
        assert position.quantity == 1.0
        assert position.average_price == 98.0

    def test_stop_loss_execution(self):
        """Test stop loss order execution."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        # Open long position with stop loss
        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)
        sim.place_order(
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=1.0,
            stop_loss=95.0,
        )

        # Verify SL order was created
        assert len(sim.get_pending_orders()) == 1

        # Price drops to trigger stop loss
        candle2 = create_candle(96, 97, 94, 95, 1000)
        trades = sim.update_market(candle2)

        # Stop loss should have executed
        assert len(trades) == 1
        position = sim.get_position()
        assert position.is_flat

        pnl = sim.get_pnl()
        assert pnl["realized"] == -5.0  # Loss: 95 - 100

    def test_take_profit_execution(self):
        """Test take profit order execution."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        # Open long position with take profit
        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)
        sim.place_order(
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=1.0,
            take_profit=110.0,
        )

        # Verify TP order was created
        assert len(sim.get_pending_orders()) == 1

        # Price rises to trigger take profit
        candle2 = create_candle(108, 111, 107, 110, 1000)
        trades = sim.update_market(candle2)

        # Take profit should have executed
        assert len(trades) == 1
        position = sim.get_position()
        assert position.is_flat

        pnl = sim.get_pnl()
        assert pnl["realized"] == 10.0  # Profit: 110 - 100

    def test_get_state(self):
        """Test get_state method."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 1.0)

        state = sim.get_state()
        assert state["balance"] == 10000
        assert state["position"]["quantity"] == 1.0
        assert state["position"]["side"] == "BUY"
        assert state["last_price"] == 100
        assert "equity" in state

    def test_reset(self):
        """Test simulator reset."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.001)

        # Do some trading
        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 1.0)

        # Reset
        sim.reset()

        # Check everything is reset
        assert sim.balance == 10000
        assert sim.get_position().is_flat
        assert len(sim.get_trade_history()) == 0
        assert len(sim.get_pending_orders()) == 0


class TestPnLModes:
    """Test different PnL calculation modes."""

    def test_fiat_mode(self):
        """Test FIAT PnL mode."""
        sim = TradingSimulator(
            initial_balance=10000,
            pnl_mode=PnLMode.FIAT,
            fee_rate=0.0,
        )

        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 1.0)

        candle2 = create_candle(105, 106, 104, 105, 1000)
        sim.update_market(candle2)

        pnl = sim.get_pnl()
        assert pnl["unrealized"] == 5.0  # (105 - 100) * 1

    def test_ticks_mode(self):
        """Test TICKS PnL mode."""
        sim = TradingSimulator(
            initial_balance=10000,
            pnl_mode=PnLMode.TICKS,
            tick_size=0.25,
            tick_value=12.5,
            fee_rate=0.0,
        )

        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 1.0)

        candle2 = create_candle(101, 102, 100, 101, 1000)
        sim.update_market(candle2)

        pnl = sim.get_pnl()
        # Price diff = 1, ticks = 1/0.25 = 4, PnL = 4 * 12.5 * 1 = 50
        assert pnl["unrealized"] == 50.0

    def test_pips_mode(self):
        """Test PIPS PnL mode."""
        sim = TradingSimulator(
            initial_balance=200000,  # Sufficient balance for 1 forex lot
            pnl_mode=PnLMode.PIPS,
            pip_position=4,
            contract_size=100000,
            fee_rate=0.0,
        )

        candle = create_candle(1.1000, 1.1010, 1.0990, 1.1000, 1000)
        sim.update_market(candle)
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 1.0)

        candle2 = create_candle(1.1010, 1.1020, 1.1005, 1.1010, 1000)
        sim.update_market(candle2)

        pnl = sim.get_pnl()
        # Price diff = 0.001, pips = 0.001 * 10000 = 10 pips
        # Pip value = 100000 / 10000 = 10
        # PnL = 10 * 10 * 1 = 100
        assert pnl["unrealized"] == pytest.approx(100.0)

    def test_points_mode(self):
        """Test POINTS PnL mode."""
        sim = TradingSimulator(
            initial_balance=10000,
            pnl_mode=PnLMode.POINTS,
            fee_rate=0.0,
        )

        candle = create_candle(4500, 4510, 4490, 4500, 1000)
        sim.update_market(candle)
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 1.0)

        candle2 = create_candle(4510, 4520, 4505, 4515, 1000)
        sim.update_market(candle2)

        pnl = sim.get_pnl()
        # Price diff = 15 points
        assert pnl["unrealized"] == 15.0


class TestPositionReversal:
    """Test position reversal scenarios."""

    def test_reverse_long_to_short(self):
        """Test reversing from long to short position."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        # Open long position
        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 1.0)

        # Price moves up
        candle2 = create_candle(105, 106, 104, 105, 1000)
        sim.update_market(candle2)

        # Reverse: sell 2 (close 1 long, open 1 short)
        sim.place_order(OrderType.MARKET, OrderSide.SELL, 2.0)

        position = sim.get_position()
        assert position.quantity == -1.0  # Now short 1
        assert position.average_price == 105.0

        pnl = sim.get_pnl()
        assert pnl["realized"] == 5.0  # Profit from closed long (105 - 100)

    def test_reverse_short_to_long(self):
        """Test reversing from short to long position."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        # Open short position
        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)
        sim.place_order(OrderType.MARKET, OrderSide.SELL, 1.0)

        # Price moves down
        candle2 = create_candle(95, 96, 94, 95, 1000)
        sim.update_market(candle2)

        # Reverse: buy 2 (close 1 short, open 1 long)
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 2.0)

        position = sim.get_position()
        assert position.quantity == 1.0  # Now long 1
        assert position.average_price == 95.0

        pnl = sim.get_pnl()
        assert pnl["realized"] == 5.0  # Profit from closed short (100 - 95)

    def test_partial_close_long(self):
        """Test partially closing a long position."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        # Open long position of 3 units
        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 3.0)

        # Price moves up
        candle2 = create_candle(110, 111, 109, 110, 1000)
        sim.update_market(candle2)

        # Partially close: sell 2 out of 3
        sim.place_order(OrderType.MARKET, OrderSide.SELL, 2.0)

        position = sim.get_position()
        assert position.quantity == 1.0  # Still long 1
        assert position.average_price == 100.0  # Original entry price

        pnl = sim.get_pnl()
        assert pnl["realized"] == 20.0  # (110 - 100) * 2
        assert pnl["unrealized"] == 10.0  # (110 - 100) * 1

    def test_partial_close_short(self):
        """Test partially closing a short position."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        # Open short position of 3 units
        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)
        sim.place_order(OrderType.MARKET, OrderSide.SELL, 3.0)

        # Price moves down
        candle2 = create_candle(90, 91, 89, 90, 1000)
        sim.update_market(candle2)

        # Partially close: buy 2 out of 3
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 2.0)

        position = sim.get_position()
        assert position.quantity == -1.0  # Still short 1
        assert position.average_price == 100.0  # Original entry price

        pnl = sim.get_pnl()
        assert pnl["realized"] == 20.0  # (100 - 90) * 2
        assert pnl["unrealized"] == 10.0  # (100 - 90) * 1


class TestOrderManagement:
    """Test order management features."""

    def test_cancel_pending_limit_order(self):
        """Test cancelling a pending limit order."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)

        # Place limit order
        order = sim.place_order(
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=1.0,
            price=95.0,
        )

        assert len(sim.get_pending_orders()) == 1

        # Cancel the order
        success = sim.cancel_order(order.order_id)
        assert success
        assert len(sim.get_pending_orders()) == 0

    def test_cancel_nonexistent_order(self):
        """Test cancelling a non-existent order."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)

        # Try to cancel non-existent order
        success = sim.cancel_order("fake_order_id")
        assert not success

    def test_multiple_pending_orders(self):
        """Test multiple pending orders."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)

        # Place multiple orders
        sim.place_order(OrderType.LIMIT, OrderSide.BUY, 1.0, price=95.0)
        sim.place_order(OrderType.LIMIT, OrderSide.SELL, 1.0, price=105.0)
        sim.place_order(OrderType.STOP_LOSS, OrderSide.SELL, 1.0, price=90.0)

        assert len(sim.get_pending_orders()) == 3

    def test_limit_order_not_triggered(self):
        """Test that limit order doesn't execute when price doesn't reach it."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)

        # Place buy limit at 95
        sim.place_order(OrderType.LIMIT, OrderSide.BUY, 1.0, price=95.0)

        # Price stays above limit
        candle2 = create_candle(100, 102, 98, 101, 1000)
        trades = sim.update_market(candle2)

        assert len(trades) == 0  # No execution
        assert len(sim.get_pending_orders()) == 1  # Still pending


class TestErrorHandling:
    """Test error handling."""

    def test_insufficient_balance(self):
        """Test placing order with insufficient balance."""
        sim = TradingSimulator(initial_balance=100, fee_rate=0.0)

        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)

        # Try to buy more than balance allows
        with pytest.raises(RuntimeError, match="Insufficient balance"):
            sim.place_order(OrderType.MARKET, OrderSide.BUY, 10.0)

    def test_market_order_without_market_data(self):
        """Test placing market order before any market data."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        # Try to place market order without calling update_market first
        with pytest.raises(RuntimeError, match="No market data available"):
            sim.place_order(OrderType.MARKET, OrderSide.BUY, 1.0)

    def test_limit_order_without_price(self):
        """Test placing limit order without specifying price."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)

        # Try to place limit order without price
        with pytest.raises(ValueError, match="require a price"):
            sim.place_order(OrderType.LIMIT, OrderSide.BUY, 1.0)


class TestFeesAndSlippage:
    """Test fees and slippage calculations."""

    def test_fees_deducted_from_balance(self):
        """Test that fees are properly deducted from balance."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.001)

        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)

        initial_balance = sim.balance
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 1.0)

        # Fee should be 100 * 1 * 0.001 = 0.1
        expected_fee = 0.1
        assert sim.balance == initial_balance - expected_fee

    def test_fees_in_pnl_summary(self):
        """Test that fees are included in PnL summary."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.001)

        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 1.0)

        candle2 = create_candle(110, 111, 109, 110, 1000)
        sim.update_market(candle2)
        sim.place_order(OrderType.MARKET, OrderSide.SELL, 1.0)

        pnl = sim.get_pnl()
        # Opening fee: 100 * 1 * 0.001 = 0.1
        # Closing fee: 110 * 1 * 0.001 = 0.11
        # Total fees tracked: 0.21
        assert pnl["fees"] == pytest.approx(0.21)
        # Realized PnL has closing fee deducted: 10.0 - 0.11 = 9.89
        assert pnl["realized"] == pytest.approx(10.0 - 0.11)
        # Net = realized (already includes closing fee deduction)
        assert pnl["net"] == pytest.approx(9.89)
        # Total is same as net
        assert pnl["total"] == pnl["net"]


class TestTradeHistory:
    """Test trade history tracking."""

    def test_trade_history_records_all_trades(self):
        """Test that all trades are recorded in history."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.0)

        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)

        # Make multiple trades
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 1.0)
        sim.place_order(OrderType.MARKET, OrderSide.SELL, 1.0)
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 2.0)

        history = sim.get_trade_history()
        assert len(history) == 3

    def test_trade_history_contains_details(self):
        """Test that trade history contains all relevant details."""
        sim = TradingSimulator(initial_balance=10000, fee_rate=0.001)

        candle = create_candle(100, 101, 99, 100, 1000)
        sim.update_market(candle)
        sim.place_order(OrderType.MARKET, OrderSide.BUY, 1.5)

        history = sim.get_trade_history()
        assert len(history) == 1

        trade = history[0]
        assert trade.side == OrderSide.BUY
        assert trade.quantity == 1.5
        assert trade.price == 100
        assert trade.fees == pytest.approx(0.15)
        assert trade.trade_id is not None


class TestLeverageAndMargin:
    """Test leverage and margin calculations."""

    def test_leverage_reduces_required_margin(self):
        """Test that leverage reduces required margin."""
        # No leverage
        sim1 = TradingSimulator(
            initial_balance=1000,
            fee_rate=0.0,
            leverage=1.0,
        )

        # 10x leverage
        sim2 = TradingSimulator(
            initial_balance=1000,
            fee_rate=0.0,
            leverage=10.0,
        )

        candle = create_candle(100, 101, 99, 100, 1000)

        # Without leverage, can't buy 11 units (requires 1100 > 1000 balance)
        sim1.update_market(candle)
        with pytest.raises(RuntimeError, match="Insufficient balance"):
            sim1.place_order(OrderType.MARKET, OrderSide.BUY, 11.0)

        # With 10x leverage, can buy 10 units (requires only 100)
        sim2.update_market(candle)
        order = sim2.place_order(OrderType.MARKET, OrderSide.BUY, 10.0)
        assert order.status == OrderStatus.FILLED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
