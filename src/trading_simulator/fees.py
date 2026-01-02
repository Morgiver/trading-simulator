"""Fee calculation for trading operations."""

from .enums import PnLMode


class FeeCalculator:
    """Calculate trading fees based on PnL mode."""

    def __init__(
        self,
        fee_rate: float = 0.0,
        fixed_fee: float = 0.0,
        min_fee: float = 0.0,
        max_fee: float = float('inf'),
    ):
        """
        Initialize fee calculator.

        Args:
            fee_rate: Percentage fee rate (e.g., 0.001 = 0.1%)
            fixed_fee: Fixed fee per trade
            min_fee: Minimum fee per trade
            max_fee: Maximum fee per trade
        """
        self.fee_rate = fee_rate
        self.fixed_fee = fixed_fee
        self.min_fee = min_fee
        self.max_fee = max_fee

    def calculate_fee(
        self,
        price: float,
        quantity: float,
        pnl_mode: PnLMode,
        contract_size: float = 100000,
    ) -> float:
        """
        Calculate trading fee.

        Args:
            price: Execution price
            quantity: Order quantity
            pnl_mode: PnL calculation mode
            contract_size: Contract size (for PIPS mode)

        Returns:
            Fee amount
        """
        # Calculate base fee based on notional value
        if pnl_mode == PnLMode.FIAT:
            notional_value = price * quantity
        elif pnl_mode == PnLMode.TICKS:
            notional_value = price * quantity
        elif pnl_mode == PnLMode.PIPS:
            notional_value = price * contract_size * quantity
        elif pnl_mode == PnLMode.POINTS:
            notional_value = price * quantity
        else:
            raise ValueError(f"Unknown PnL mode: {pnl_mode}")

        # Calculate percentage-based fee
        percentage_fee = notional_value * self.fee_rate

        # Add fixed fee
        total_fee = percentage_fee + self.fixed_fee

        # Apply min/max limits
        total_fee = max(self.min_fee, min(self.max_fee, total_fee))

        return total_fee

    def calculate_slippage(
        self,
        price: float,
        slippage_rate: float = 0.0,
    ) -> float:
        """
        Calculate slippage (price impact).

        Args:
            price: Expected execution price
            slippage_rate: Slippage as percentage (e.g., 0.0001 = 0.01%)

        Returns:
            Slippage amount in price units
        """
        return price * slippage_rate
