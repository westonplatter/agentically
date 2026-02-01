"""
Options Liquidity Heatmap Skill

A skill for visualizing options chain liquidity using 3D heatmaps.
Uses Alpaca's official Python SDK for real-time options data.

Features:
- Fetch real-time options chain data from Alpaca
- Cache data locally for analysis
- Generate 3D heatmaps showing liquidity across DTE and strikes/moneyness/delta
- Support for volume and open interest metrics (absolute and percentage)
"""

from .fetcher import OptionsChainFetcher
from .heatmap import LiquidityHeatmap
from .cache import DataCache
from .models import (
    OptionsChainData,
    HeatmapConfig,
    YAxisMode,
    ValueMode,
)

__all__ = [
    "OptionsChainFetcher",
    "LiquidityHeatmap",
    "DataCache",
    "OptionsChainData",
    "HeatmapConfig",
    "YAxisMode",
    "ValueMode",
]

__version__ = "0.1.0"
