"""
Data models and type definitions for options liquidity analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal


class YAxisMode(Enum):
    """Y-axis display mode for the heatmap."""

    STRIKE = "strike"  # Absolute strike prices
    MONEYNESS = "moneyness"  # Strike / Underlying price (1.0 = ATM)
    DELTA = "delta"  # Option delta (-1 to 1)


class ValueMode(Enum):
    """Value mode for heatmap bins."""

    OPEN_INTEREST_ABSOLUTE = "oi_absolute"  # Raw open interest
    OPEN_INTEREST_PERCENT = "oi_percent"  # OI as % of total OI for that DTE
    VOLUME_ABSOLUTE = "volume_absolute"  # Raw volume
    VOLUME_PERCENT = "volume_percent"  # Volume as % of total volume for that DTE


@dataclass
class OptionContract:
    """Single option contract data."""

    symbol: str  # OCC symbol
    underlying_symbol: str
    expiration_date: datetime
    strike_price: float
    option_type: Literal["call", "put"]
    open_interest: int
    volume: int
    bid: float
    ask: float
    last_price: float
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    implied_volatility: float | None = None


@dataclass
class OptionsChainData:
    """Complete options chain data for a ticker."""

    underlying_symbol: str
    underlying_price: float
    fetch_timestamp: datetime
    contracts: list[OptionContract] = field(default_factory=list)

    @property
    def expirations(self) -> list[datetime]:
        """Get unique expiration dates sorted ascending."""
        dates = sorted(set(c.expiration_date for c in self.contracts))
        return dates

    @property
    def strikes(self) -> list[float]:
        """Get unique strike prices sorted ascending."""
        return sorted(set(c.strike_price for c in self.contracts))

    @property
    def calls(self) -> list[OptionContract]:
        """Get all call contracts."""
        return [c for c in self.contracts if c.option_type == "call"]

    @property
    def puts(self) -> list[OptionContract]:
        """Get all put contracts."""
        return [c for c in self.contracts if c.option_type == "put"]

    def filter_by_expiration(self, expiration: datetime) -> list[OptionContract]:
        """Get contracts for a specific expiration."""
        return [c for c in self.contracts if c.expiration_date == expiration]

    def filter_by_strike(self, strike: float) -> list[OptionContract]:
        """Get contracts for a specific strike."""
        return [c for c in self.contracts if c.strike_price == strike]


@dataclass
class HeatmapConfig:
    """Configuration for heatmap generation."""

    y_axis_mode: YAxisMode = YAxisMode.STRIKE
    value_mode: ValueMode = ValueMode.OPEN_INTEREST_ABSOLUTE
    option_type: Literal["call", "put", "both"] = "both"
    min_dte: int = 0  # Minimum days to expiration
    max_dte: int = 90  # Maximum days to expiration
    min_moneyness: float = 0.8  # For moneyness mode: min strike/underlying
    max_moneyness: float = 1.2  # For moneyness mode: max strike/underlying
    colorscale: str = "Viridis"  # Plotly colorscale
    title: str | None = None  # Custom title (auto-generated if None)
    show_annotations: bool = False  # Show values in cells
    height: int = 800
    width: int = 1200
