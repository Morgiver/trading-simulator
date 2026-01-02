"""Order management and execution logic."""

from typing import List, Optional
from datetime import datetime
from trading_frame import Candle
from .models import Order, Trade
from .enums import OrderType, OrderSide, OrderStatus
from .fees import FeeCalculator
from .enums import PnLMode


class OrderManager:
    """Manages pending orders and their execution."""

    def __init__(
        self,
        fee_calculator: FeeCalculator,
        pnl_mode: PnLMode,
        contract_size: float = 100000,
    ):
        """
        Initialize order manager.

        Args:
            fee_calculator: Fee calculator instance
            pnl_mode: PnL calculation mode
            contract_size: Contract size (for PIPS mode)
        """
        self.fee_calculator = fee_calculator
        self.pnl_mode = pnl_mode
        self.contract_size = contract_size
        self.pending_orders: List[Order] = []
        self.filled_orders: List[Order] = []

    def add_order(self, order: Order) -> Order:
        """
        Add a new order to the pending list.

        Args:
            order: Order to add

        Returns:
            The added order
        """
        if order.order_type == OrderType.MARKET:
            # Market orders don't go to pending, they execute immediately
            raise ValueError("Market orders should be executed immediately, not added to pending")

        self.pending_orders.append(order)
        return order

    def execute_market_order(self, order: Order, current_price: float) -> Trade:
        """
        Execute a market order immediately.

        Args:
            order: Market order to execute
            current_price: Current market price

        Returns:
            Executed trade
        """
        if order.order_type != OrderType.MARKET:
            raise ValueError("Only market orders can be executed immediately")

        # Calculate fees
        fees = self.fee_calculator.calculate_fee(
            current_price,
            order.quantity,
            self.pnl_mode,
            self.contract_size,
        )

        # Update order
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now()
        order.filled_price = current_price
        order.fees = fees

        # Create trade
        trade = Trade(
            side=order.side,
            quantity=order.quantity,
            price=current_price,
            fees=fees,
            timestamp=order.filled_at,
        )

        self.filled_orders.append(order)
        return trade

    def update_orders(self, candle: Candle) -> List[Trade]:
        """
        Check and execute pending orders based on candle data.

        Args:
            candle: Current candle data

        Returns:
            List of executed trades
        """
        executed_trades = []
        orders_to_remove = []

        for order in self.pending_orders:
            trade = self._check_order_execution(order, candle)
            if trade:
                executed_trades.append(trade)
                orders_to_remove.append(order)
                self.filled_orders.append(order)

        # Remove executed orders from pending
        for order in orders_to_remove:
            self.pending_orders.remove(order)

        return executed_trades

    def _check_order_execution(self, order: Order, candle: Candle) -> Optional[Trade]:
        """
        Check if an order should be executed based on candle data.

        Args:
            order: Order to check
            candle: Current candle

        Returns:
            Trade if executed, None otherwise
        """
        execution_price = None

        if order.order_type == OrderType.LIMIT:
            execution_price = self._check_limit_order(order, candle)
        elif order.order_type == OrderType.STOP_LOSS:
            execution_price = self._check_stop_order(order, candle)
        elif order.order_type == OrderType.TAKE_PROFIT:
            execution_price = self._check_take_profit_order(order, candle)

        if execution_price is not None:
            # Execute the order
            fees = self.fee_calculator.calculate_fee(
                execution_price,
                order.quantity,
                self.pnl_mode,
                self.contract_size,
            )

            order.status = OrderStatus.FILLED
            order.filled_at = datetime.now()
            order.filled_price = execution_price
            order.fees = fees

            trade = Trade(
                side=order.side,
                quantity=order.quantity,
                price=execution_price,
                fees=fees,
                timestamp=order.filled_at,
            )

            return trade

        return None

    def _check_limit_order(self, order: Order, candle: Candle) -> Optional[float]:
        """
        Check if a limit order should be executed.

        Buy limit: Execute if price drops to or below limit price
        Sell limit: Execute if price rises to or above limit price
        """
        if order.price is None:
            return None

        if order.side == OrderSide.BUY:
            # Buy limit: waiting for price to drop to limit
            if candle.low_price <= order.price:
                return order.price
        else:  # SELL
            # Sell limit: waiting for price to rise to limit
            if candle.high_price >= order.price:
                return order.price

        return None

    def _check_stop_order(self, order: Order, candle: Candle) -> Optional[float]:
        """
        Check if a stop order should be executed.

        Buy stop: Execute if price rises to or above stop price (stop buy)
        Sell stop: Execute if price drops to or below stop price (stop loss)
        """
        if order.price is None:
            return None

        if order.side == OrderSide.BUY:
            # Buy stop: waiting for price to rise to stop
            if candle.high_price >= order.price:
                return order.price
        else:  # SELL
            # Sell stop: waiting for price to drop to stop
            if candle.low_price <= order.price:
                return order.price

        return None

    def _check_take_profit_order(self, order: Order, candle: Candle) -> Optional[float]:
        """
        Check if a take profit order should be executed.

        Same logic as limit orders.
        """
        return self._check_limit_order(order, candle)

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.

        Args:
            order_id: ID of the order to cancel

        Returns:
            True if cancelled, False if not found
        """
        for order in self.pending_orders:
            if order.order_id == order_id:
                order.status = OrderStatus.CANCELLED
                self.pending_orders.remove(order)
                return True
        return False

    def get_pending_orders(self) -> List[Order]:
        """Get all pending orders."""
        return self.pending_orders.copy()

    def get_filled_orders(self) -> List[Order]:
        """Get all filled orders."""
        return self.filled_orders.copy()

    def clear_filled_orders(self):
        """Clear the filled orders history."""
        self.filled_orders.clear()
