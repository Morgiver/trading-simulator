"""Main trading simulator API."""

from typing import Optional, List, Dict, Any
from .models import Order, Position, Trade, Candle
from .enums import OrderType, OrderSide, PnLMode, OrderStatus
from .pnl_calculator import PnLCalculator
from .fees import FeeCalculator
from .order_manager import OrderManager
from .position_manager import PositionManager


class TradingSimulator:
    """
    Main trading simulator for backtesting and reinforcement learning.

    This simulator manages positions, orders, PnL calculation, and trade execution.
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        pnl_mode: PnLMode = PnLMode.FIAT,
        fee_rate: float = 0.0,
        fixed_fee: float = 0.0,
        min_fee: float = 0.0,
        max_fee: float = float('inf'),
        tick_size: float = 0.01,
        tick_value: float = 1.0,
        pip_position: int = 4,
        contract_size: float = 100000,
        leverage: float = 1.0,
    ):
        """
        Initialize the trading simulator.

        Args:
            initial_balance: Starting balance
            pnl_mode: PnL calculation mode (FIAT, TICKS, PIPS, POINTS)
            fee_rate: Percentage fee rate (e.g., 0.001 = 0.1%)
            fixed_fee: Fixed fee per trade
            min_fee: Minimum fee per trade
            max_fee: Maximum fee per trade
            tick_size: Size of one tick (for TICKS mode)
            tick_value: Value of one tick (for TICKS mode)
            pip_position: Decimal position of pip (for PIPS mode)
            contract_size: Contract size for forex (for PIPS mode)
            leverage: Leverage ratio (1.0 = no leverage)
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.pnl_mode = pnl_mode
        self.leverage = leverage

        # Initialize components
        self.pnl_calculator = PnLCalculator(
            mode=pnl_mode,
            tick_size=tick_size,
            tick_value=tick_value,
            pip_position=pip_position,
            contract_size=contract_size,
        )

        self.fee_calculator = FeeCalculator(
            fee_rate=fee_rate,
            fixed_fee=fixed_fee,
            min_fee=min_fee,
            max_fee=max_fee,
        )

        self.order_manager = OrderManager(
            fee_calculator=self.fee_calculator,
            pnl_mode=pnl_mode,
            contract_size=contract_size,
        )

        self.position_manager = PositionManager(
            pnl_calculator=self.pnl_calculator,
        )

        # Current market state
        self.current_candle: Optional[Candle] = None
        self.last_price: Optional[float] = None

    def place_order(
        self,
        order_type: OrderType,
        side: OrderSide,
        quantity: float,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Order:
        """
        Place a trading order.

        Args:
            order_type: Type of order (MARKET, LIMIT, STOP_LOSS, TAKE_PROFIT)
            side: Order side (BUY or SELL)
            quantity: Order quantity
            price: Limit/stop price (required for non-market orders)
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)

        Returns:
            Created order

        Raises:
            ValueError: If order parameters are invalid
            RuntimeError: If insufficient balance
        """
        # Validate price for non-market orders
        if order_type != OrderType.MARKET and price is None:
            raise ValueError(f"{order_type.name} orders require a price")

        # Create order
        order = Order(
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        # Execute market orders immediately
        if order_type == OrderType.MARKET:
            if self.last_price is None:
                raise RuntimeError("No market data available. Call update_market() first.")

            # Check if we have sufficient balance
            required_margin = self.pnl_calculator.calculate_required_margin(
                self.last_price, quantity, self.leverage
            )
            if required_margin > self.balance:
                order.status = OrderStatus.REJECTED
                raise RuntimeError(f"Insufficient balance. Required: {required_margin}, Available: {self.balance}")

            # Execute the order
            trade = self.order_manager.execute_market_order(order, self.last_price)
            self.position_manager.update_position(trade)
            self.position_manager.update_unrealized_pnl(self.last_price)

            # Update balance (deduct fees)
            self.balance -= trade.fees

        else:
            # Add to pending orders
            self.order_manager.add_order(order)

        # Create SL/TP orders if specified
        if stop_loss is not None and order_type == OrderType.MARKET:
            self._create_stop_loss_order(side, quantity, stop_loss)

        if take_profit is not None and order_type == OrderType.MARKET:
            self._create_take_profit_order(side, quantity, take_profit)

        return order

    def _create_stop_loss_order(self, original_side: OrderSide, quantity: float, stop_loss: float):
        """Create a stop loss order for a position."""
        # Stop loss is opposite side to close position
        sl_side = OrderSide.SELL if original_side == OrderSide.BUY else OrderSide.BUY
        sl_order = Order(
            order_type=OrderType.STOP_LOSS,
            side=sl_side,
            quantity=quantity,
            price=stop_loss,
        )
        self.order_manager.add_order(sl_order)

    def _create_take_profit_order(self, original_side: OrderSide, quantity: float, take_profit: float):
        """Create a take profit order for a position."""
        # Take profit is opposite side to close position
        tp_side = OrderSide.SELL if original_side == OrderSide.BUY else OrderSide.BUY
        tp_order = Order(
            order_type=OrderType.TAKE_PROFIT,
            side=tp_side,
            quantity=quantity,
            price=take_profit,
        )
        self.order_manager.add_order(tp_order)

    def update_market(self, candle: Candle) -> List[Trade]:
        """
        Update simulator with new market data.

        This will check and execute pending orders and update unrealized PnL.

        Args:
            candle: New candlestick data

        Returns:
            List of trades executed during this update
        """
        self.current_candle = candle
        self.last_price = candle.close

        # Check and execute pending orders
        executed_trades = self.order_manager.update_orders(candle)

        # Update position with executed trades
        for trade in executed_trades:
            self.position_manager.update_position(trade)
            self.balance -= trade.fees

        # Update unrealized PnL
        self.position_manager.update_unrealized_pnl(candle.close)

        return executed_trades

    def get_position(self) -> Position:
        """
        Get current position.

        Returns:
            Current position
        """
        return self.position_manager.get_position()

    def get_pnl(self) -> Dict[str, float]:
        """
        Get PnL summary.

        Returns:
            Dictionary with realized, unrealized, total, fees, and net PnL
        """
        return self.position_manager.get_pnl_summary()

    def get_trade_history(self) -> List[Trade]:
        """
        Get trade history.

        Returns:
            List of all executed trades
        """
        return self.position_manager.get_trade_history()

    def get_pending_orders(self) -> List[Order]:
        """
        Get pending orders.

        Returns:
            List of pending orders
        """
        return self.order_manager.get_pending_orders()

    def get_filled_orders(self) -> List[Order]:
        """
        Get filled orders.

        Returns:
            List of filled orders
        """
        return self.order_manager.get_filled_orders()

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.

        Args:
            order_id: ID of the order to cancel

        Returns:
            True if cancelled, False if not found
        """
        return self.order_manager.cancel_order(order_id)

    def get_state(self) -> Dict[str, Any]:
        """
        Get complete simulator state (useful for RL).

        Returns:
            Dictionary with all relevant state information
        """
        position = self.get_position()
        pnl = self.get_pnl()

        return {
            "balance": self.balance,
            "position": {
                "quantity": position.quantity,
                "average_price": position.average_price,
                "side": position.side.name if position.side else None,
                "is_flat": position.is_flat,
            },
            "pnl": pnl,
            "last_price": self.last_price,
            "pending_orders_count": len(self.get_pending_orders()),
            "equity": self.balance + pnl["net"],
        }

    def reset(self) -> None:
        """Reset the simulator to initial state."""
        self.balance = self.initial_balance
        self.current_candle = None
        self.last_price = None
        self.position_manager.reset()
        self.order_manager.pending_orders.clear()
        self.order_manager.filled_orders.clear()
