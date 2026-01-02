"""PnL calculation for different modes."""

from .enums import PnLMode, OrderSide


class PnLCalculator:
    """Calculate Profit and Loss based on different modes."""

    def __init__(
        self,
        mode: PnLMode,
        tick_size: float = 0.01,
        tick_value: float = 1.0,
        pip_position: int = 4,  # 4 decimal places for most forex pairs
        contract_size: float = 100000,  # Standard forex lot
    ):
        """
        Initialize PnL calculator.

        Args:
            mode: PnL calculation mode
            tick_size: Size of one tick (for TICKS mode)
            tick_value: Value of one tick in base currency (for TICKS mode)
            pip_position: Decimal position of pip (for PIPS mode)
            contract_size: Contract size for forex (for PIPS mode)
        """
        self.mode = mode
        self.tick_size = tick_size
        self.tick_value = tick_value
        self.pip_position = pip_position
        self.contract_size = contract_size

    def calculate_pnl(
        self,
        entry_price: float,
        current_price: float,
        quantity: float,
        side: OrderSide,
    ) -> float:
        """
        Calculate PnL based on the configured mode.

        Args:
            entry_price: Entry price of the position
            current_price: Current market price
            quantity: Position size (absolute value)
            side: Position side (BUY or SELL)

        Returns:
            PnL value in the appropriate unit
        """
        # Calculate price difference with direction
        if side == OrderSide.BUY:
            price_diff = current_price - entry_price
        else:  # SELL
            price_diff = entry_price - current_price

        # Calculate based on mode
        if self.mode == PnLMode.FIAT:
            return self._calculate_fiat_pnl(price_diff, quantity)
        elif self.mode == PnLMode.TICKS:
            return self._calculate_ticks_pnl(price_diff, quantity)
        elif self.mode == PnLMode.PIPS:
            return self._calculate_pips_pnl(price_diff, quantity)
        elif self.mode == PnLMode.POINTS:
            return self._calculate_points_pnl(price_diff, quantity)
        else:
            raise ValueError(f"Unknown PnL mode: {self.mode}")

    def _calculate_fiat_pnl(self, price_diff: float, quantity: float) -> float:
        """Calculate PnL in fiat currency (USD, EUR, etc.)."""
        return price_diff * quantity

    def _calculate_ticks_pnl(self, price_diff: float, quantity: float) -> float:
        """
        Calculate PnL in ticks (futures contracts).

        Formula: (price_diff / tick_size) * tick_value * quantity
        """
        num_ticks = price_diff / self.tick_size
        return num_ticks * self.tick_value * quantity

    def _calculate_pips_pnl(self, price_diff: float, quantity: float) -> float:
        """
        Calculate PnL in pips (forex).

        Formula: (price_diff * 10^pip_position) * (contract_size / 10^pip_position) * quantity
        Simplified: price_diff * contract_size * quantity
        """
        # For display, convert to pips
        pips = price_diff * (10 ** self.pip_position)
        # Calculate monetary value
        pip_value = (self.contract_size / (10 ** self.pip_position))
        return pips * pip_value * quantity

    def _calculate_points_pnl(self, price_diff: float, quantity: float) -> float:
        """
        Calculate PnL in points (index trading).

        Similar to fiat but often with different multipliers per point.
        """
        return price_diff * quantity

    def calculate_required_margin(
        self,
        price: float,
        quantity: float,
        leverage: float = 1.0
    ) -> float:
        """
        Calculate required margin for a position.

        Args:
            price: Entry price
            quantity: Position size
            leverage: Leverage ratio (1.0 = no leverage)

        Returns:
            Required margin amount
        """
        if self.mode == PnLMode.FIAT:
            notional_value = price * quantity
            return notional_value / leverage
        elif self.mode == PnLMode.TICKS:
            # For futures, margin is typically based on contract value
            notional_value = price * quantity
            return notional_value / leverage
        elif self.mode == PnLMode.PIPS:
            # For forex
            notional_value = price * self.contract_size * quantity
            return notional_value / leverage
        elif self.mode == PnLMode.POINTS:
            notional_value = price * quantity
            return notional_value / leverage
        else:
            raise ValueError(f"Unknown PnL mode: {self.mode}")
