"""Position management and PnL tracking."""

from typing import List, Optional
from .models import Position, Trade
from .enums import OrderSide
from .pnl_calculator import PnLCalculator


class PositionManager:
    """Manages the current position and calculates PnL."""

    def __init__(self, pnl_calculator: PnLCalculator):
        """
        Initialize position manager.

        Args:
            pnl_calculator: PnL calculator instance
        """
        self.pnl_calculator = pnl_calculator
        self.position = Position()
        self.trade_history: List[Trade] = []

    def update_position(self, trade: Trade) -> None:
        """
        Update position based on a new trade.

        Args:
            trade: Executed trade
        """
        # Add to trade history
        self.trade_history.append(trade)

        # Calculate total fees
        self.position.total_fees += trade.fees

        # Handle position update based on direction
        if trade.side == OrderSide.BUY:
            self._handle_buy(trade)
        else:  # SELL
            self._handle_sell(trade)

    def _handle_buy(self, trade: Trade) -> None:
        """Handle a buy trade."""
        current_qty = self.position.quantity

        if current_qty == 0:
            # Opening a long position
            self.position.quantity = trade.quantity
            self.position.average_price = trade.price
            trade.pnl = 0.0  # No realized PnL on opening

        elif current_qty > 0:
            # Adding to long position
            total_cost = (self.position.average_price * self.position.quantity) + (trade.price * trade.quantity)
            self.position.quantity += trade.quantity
            self.position.average_price = total_cost / self.position.quantity
            trade.pnl = 0.0  # No realized PnL on adding

        else:  # current_qty < 0 (short position)
            # Closing or reversing short position
            if abs(current_qty) >= trade.quantity:
                # Partially or fully closing short
                realized_pnl = self.pnl_calculator.calculate_pnl(
                    self.position.average_price,
                    trade.price,
                    trade.quantity,
                    OrderSide.SELL,  # Original position side
                )
                realized_pnl -= trade.fees  # Subtract fees from PnL
                self.position.realized_pnl += realized_pnl
                trade.pnl = realized_pnl

                self.position.quantity += trade.quantity

                if self.position.quantity == 0:
                    # Position fully closed
                    self.position.average_price = 0.0

            else:
                # Reversing: close short and open long
                # First close the short position
                close_qty = abs(current_qty)
                realized_pnl = self.pnl_calculator.calculate_pnl(
                    self.position.average_price,
                    trade.price,
                    close_qty,
                    OrderSide.SELL,
                )
                realized_pnl -= (trade.fees * (close_qty / trade.quantity))  # Proportional fees
                self.position.realized_pnl += realized_pnl

                # Then open long with remaining quantity
                remaining_qty = trade.quantity - close_qty
                self.position.quantity = remaining_qty
                self.position.average_price = trade.price
                trade.pnl = realized_pnl

    def _handle_sell(self, trade: Trade) -> None:
        """Handle a sell trade."""
        current_qty = self.position.quantity

        if current_qty == 0:
            # Opening a short position
            self.position.quantity = -trade.quantity
            self.position.average_price = trade.price
            trade.pnl = 0.0  # No realized PnL on opening

        elif current_qty < 0:
            # Adding to short position
            total_cost = (self.position.average_price * abs(self.position.quantity)) + (trade.price * trade.quantity)
            self.position.quantity -= trade.quantity
            self.position.average_price = total_cost / abs(self.position.quantity)
            trade.pnl = 0.0  # No realized PnL on adding

        else:  # current_qty > 0 (long position)
            # Closing or reversing long position
            if current_qty >= trade.quantity:
                # Partially or fully closing long
                realized_pnl = self.pnl_calculator.calculate_pnl(
                    self.position.average_price,
                    trade.price,
                    trade.quantity,
                    OrderSide.BUY,  # Original position side
                )
                realized_pnl -= trade.fees  # Subtract fees from PnL
                self.position.realized_pnl += realized_pnl
                trade.pnl = realized_pnl

                self.position.quantity -= trade.quantity

                if self.position.quantity == 0:
                    # Position fully closed
                    self.position.average_price = 0.0

            else:
                # Reversing: close long and open short
                # First close the long position
                close_qty = current_qty
                realized_pnl = self.pnl_calculator.calculate_pnl(
                    self.position.average_price,
                    trade.price,
                    close_qty,
                    OrderSide.BUY,
                )
                realized_pnl -= (trade.fees * (close_qty / trade.quantity))  # Proportional fees
                self.position.realized_pnl += realized_pnl

                # Then open short with remaining quantity
                remaining_qty = trade.quantity - close_qty
                self.position.quantity = -remaining_qty
                self.position.average_price = trade.price
                trade.pnl = realized_pnl

    def update_unrealized_pnl(self, current_price: float) -> None:
        """
        Update unrealized PnL based on current market price.

        Args:
            current_price: Current market price
        """
        if self.position.quantity == 0:
            self.position.unrealized_pnl = 0.0
            return

        # Determine position side
        side = OrderSide.BUY if self.position.quantity > 0 else OrderSide.SELL

        # Calculate unrealized PnL
        self.position.unrealized_pnl = self.pnl_calculator.calculate_pnl(
            self.position.average_price,
            current_price,
            abs(self.position.quantity),
            side,
        )

    def get_position(self) -> Position:
        """Get current position."""
        return self.position

    def get_trade_history(self) -> List[Trade]:
        """Get trade history."""
        return self.trade_history.copy()

    def get_pnl_summary(self) -> dict:
        """
        Get a summary of PnL.

        Returns:
            Dictionary with realized, unrealized, and total PnL

        Note:
            - realized_pnl already has closing trade fees deducted
            - total_fees includes all fees (opening + closing)
            - net = realized + unrealized (fees already accounted for in realized)
        """
        return {
            "realized": self.position.realized_pnl,
            "unrealized": self.position.unrealized_pnl,
            "total": self.position.realized_pnl + self.position.unrealized_pnl,
            "fees": self.position.total_fees,
            "net": self.position.realized_pnl + self.position.unrealized_pnl,  # Fees already in realized
        }

    def reset(self) -> None:
        """Reset position and history."""
        self.position = Position()
        self.trade_history.clear()
