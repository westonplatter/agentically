"""
Plotly-based 3D heatmap visualization for options chain liquidity.

Creates interactive heatmaps showing:
- X-axis: Days to Expiration (DTE)
- Y-axis: Strike price / Moneyness / Delta
- Color/Z-axis: Open Interest or Volume (absolute or % of DTE)
"""

from datetime import datetime
from typing import Literal

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .models import (
    HeatmapConfig,
    OptionsChainData,
    YAxisMode,
    ValueMode,
)


class LiquidityHeatmap:
    """Creates liquidity heatmaps from options chain data."""

    def __init__(self, chain_data: OptionsChainData) -> None:
        """
        Initialize the heatmap generator.

        Args:
            chain_data: Options chain data to visualize
        """
        self.chain_data = chain_data
        self._df: pd.DataFrame | None = None

    @property
    def df(self) -> pd.DataFrame:
        """Get the options data as a DataFrame."""
        if self._df is None:
            self._df = self._build_dataframe()
        return self._df

    def _build_dataframe(self) -> pd.DataFrame:
        """Convert options chain data to DataFrame."""
        records = []
        today = datetime.now().date()

        for contract in self.chain_data.contracts:
            dte = (contract.expiration_date.date() - today).days
            moneyness = contract.strike_price / self.chain_data.underlying_price

            records.append({
                "symbol": contract.symbol,
                "expiration": contract.expiration_date,
                "dte": dte,
                "strike": contract.strike_price,
                "moneyness": moneyness,
                "option_type": contract.option_type,
                "open_interest": contract.open_interest,
                "volume": contract.volume,
                "delta": contract.delta,
                "bid": contract.bid,
                "ask": contract.ask,
                "last_price": contract.last_price,
                "iv": contract.implied_volatility,
            })

        return pd.DataFrame(records)

    def _get_y_values(self, df: pd.DataFrame, mode: YAxisMode) -> pd.Series:
        """Get Y-axis values based on mode."""
        if mode == YAxisMode.STRIKE:
            return df["strike"]
        elif mode == YAxisMode.MONEYNESS:
            return df["moneyness"]
        elif mode == YAxisMode.DELTA:
            return df["delta"].fillna(0)
        else:
            raise ValueError(f"Unknown Y-axis mode: {mode}")

    def _get_z_values(
        self,
        df: pd.DataFrame,
        mode: ValueMode,
    ) -> pd.Series:
        """Get Z-axis (color) values based on mode."""
        if mode == ValueMode.OPEN_INTEREST_ABSOLUTE:
            return df["open_interest"]

        elif mode == ValueMode.VOLUME_ABSOLUTE:
            return df["volume"]

        elif mode == ValueMode.OPEN_INTEREST_PERCENT:
            # Calculate OI as percentage of total OI for each DTE
            dte_totals = df.groupby("dte")["open_interest"].transform("sum")
            return (df["open_interest"] / dte_totals.replace(0, 1)) * 100

        elif mode == ValueMode.VOLUME_PERCENT:
            # Calculate volume as percentage of total volume for each DTE
            dte_totals = df.groupby("dte")["volume"].transform("sum")
            return (df["volume"] / dte_totals.replace(0, 1)) * 100

        else:
            raise ValueError(f"Unknown value mode: {mode}")

    def _get_colorbar_title(self, mode: ValueMode) -> str:
        """Get colorbar title based on value mode."""
        titles = {
            ValueMode.OPEN_INTEREST_ABSOLUTE: "Open Interest",
            ValueMode.OPEN_INTEREST_PERCENT: "Open Interest (% of DTE)",
            ValueMode.VOLUME_ABSOLUTE: "Volume",
            ValueMode.VOLUME_PERCENT: "Volume (% of DTE)",
        }
        return titles.get(mode, "Value")

    def _get_y_axis_title(self, mode: YAxisMode) -> str:
        """Get Y-axis title based on mode."""
        titles = {
            YAxisMode.STRIKE: "Strike Price ($)",
            YAxisMode.MONEYNESS: "Moneyness (Strike/Spot)",
            YAxisMode.DELTA: "Delta",
        }
        return titles.get(mode, "Y-Axis")

    def create_heatmap(
        self,
        config: HeatmapConfig | None = None,
    ) -> go.Figure:
        """
        Create a 2D heatmap of options liquidity.

        Args:
            config: Heatmap configuration. Uses defaults if None.

        Returns:
            Plotly Figure object
        """
        if config is None:
            config = HeatmapConfig()

        df = self.df.copy()

        # Filter by option type
        if config.option_type != "both":
            df = df[df["option_type"] == config.option_type]

        # Filter by DTE
        df = df[(df["dte"] >= config.min_dte) & (df["dte"] <= config.max_dte)]

        # Filter by moneyness if using moneyness mode
        if config.y_axis_mode == YAxisMode.MONEYNESS:
            df = df[
                (df["moneyness"] >= config.min_moneyness)
                & (df["moneyness"] <= config.max_moneyness)
            ]

        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for the specified filters",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
            return fig

        # Get Y and Z values
        df["y_value"] = self._get_y_values(df, config.y_axis_mode)
        df["z_value"] = self._get_z_values(df, config.value_mode)

        # Create pivot table for heatmap
        # Aggregate if multiple contracts per (DTE, Y) combination
        pivot_df = df.pivot_table(
            values="z_value",
            index="y_value",
            columns="dte",
            aggfunc="sum",
            fill_value=0,
        )

        # Sort index appropriately
        pivot_df = pivot_df.sort_index(ascending=True)

        # Create figure
        fig = go.Figure()

        # Add heatmap trace
        fig.add_trace(
            go.Heatmap(
                z=pivot_df.values,
                x=pivot_df.columns.tolist(),  # DTE
                y=pivot_df.index.tolist(),  # Y values
                colorscale=config.colorscale,
                colorbar=dict(
                    title=self._get_colorbar_title(config.value_mode),
                ),
                hovertemplate=(
                    f"DTE: %{{x}}<br>"
                    f"{self._get_y_axis_title(config.y_axis_mode)}: %{{y:.2f}}<br>"
                    f"{self._get_colorbar_title(config.value_mode)}: %{{z:,.0f}}"
                    "<extra></extra>"
                ),
            )
        )

        # Add annotations if enabled
        if config.show_annotations:
            for i, y_val in enumerate(pivot_df.index):
                for j, dte in enumerate(pivot_df.columns):
                    val = pivot_df.iloc[i, j]
                    if val > 0:
                        fig.add_annotation(
                            x=dte,
                            y=y_val,
                            text=f"{val:,.0f}",
                            showarrow=False,
                            font=dict(size=8, color="white"),
                        )

        # Set title
        if config.title:
            title = config.title
        else:
            opt_type = config.option_type.upper() if config.option_type != "both" else "CALLS + PUTS"
            title = (
                f"{self.chain_data.underlying_symbol} Options Liquidity Heatmap<br>"
                f"<sub>{opt_type} | Underlying: ${self.chain_data.underlying_price:.2f} | "
                f"As of: {self.chain_data.fetch_timestamp.strftime('%Y-%m-%d %H:%M:%S')}</sub>"
            )

        # Update layout
        fig.update_layout(
            title=dict(text=title, x=0.5),
            xaxis_title="Days to Expiration (DTE)",
            yaxis_title=self._get_y_axis_title(config.y_axis_mode),
            height=config.height,
            width=config.width,
            template="plotly_dark",
        )

        return fig

    def create_3d_surface(
        self,
        config: HeatmapConfig | None = None,
    ) -> go.Figure:
        """
        Create a 3D surface plot of options liquidity.

        Args:
            config: Heatmap configuration. Uses defaults if None.

        Returns:
            Plotly Figure object
        """
        if config is None:
            config = HeatmapConfig()

        df = self.df.copy()

        # Apply filters
        if config.option_type != "both":
            df = df[df["option_type"] == config.option_type]

        df = df[(df["dte"] >= config.min_dte) & (df["dte"] <= config.max_dte)]

        if config.y_axis_mode == YAxisMode.MONEYNESS:
            df = df[
                (df["moneyness"] >= config.min_moneyness)
                & (df["moneyness"] <= config.max_moneyness)
            ]

        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for the specified filters",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
            return fig

        # Get Y and Z values
        df["y_value"] = self._get_y_values(df, config.y_axis_mode)
        df["z_value"] = self._get_z_values(df, config.value_mode)

        # Create pivot table
        pivot_df = df.pivot_table(
            values="z_value",
            index="y_value",
            columns="dte",
            aggfunc="sum",
            fill_value=0,
        )

        pivot_df = pivot_df.sort_index(ascending=True)

        # Create meshgrid for 3D surface
        x = pivot_df.columns.values  # DTE
        y = pivot_df.index.values  # Y values
        z = pivot_df.values

        # Create figure
        fig = go.Figure()

        fig.add_trace(
            go.Surface(
                z=z,
                x=x,
                y=y,
                colorscale=config.colorscale,
                colorbar=dict(
                    title=self._get_colorbar_title(config.value_mode),
                ),
                hovertemplate=(
                    f"DTE: %{{x}}<br>"
                    f"{self._get_y_axis_title(config.y_axis_mode)}: %{{y:.2f}}<br>"
                    f"{self._get_colorbar_title(config.value_mode)}: %{{z:,.0f}}"
                    "<extra></extra>"
                ),
            )
        )

        # Set title
        if config.title:
            title = config.title
        else:
            opt_type = config.option_type.upper() if config.option_type != "both" else "CALLS + PUTS"
            title = (
                f"{self.chain_data.underlying_symbol} Options Liquidity 3D Surface<br>"
                f"<sub>{opt_type} | Underlying: ${self.chain_data.underlying_price:.2f}</sub>"
            )

        # Update layout
        fig.update_layout(
            title=dict(text=title, x=0.5),
            scene=dict(
                xaxis_title="Days to Expiration (DTE)",
                yaxis_title=self._get_y_axis_title(config.y_axis_mode),
                zaxis_title=self._get_colorbar_title(config.value_mode),
            ),
            height=config.height,
            width=config.width,
            template="plotly_dark",
        )

        return fig

    def create_split_heatmap(
        self,
        config: HeatmapConfig | None = None,
    ) -> go.Figure:
        """
        Create side-by-side heatmaps for calls and puts.

        Args:
            config: Heatmap configuration. Uses defaults if None.

        Returns:
            Plotly Figure object with subplots
        """
        if config is None:
            config = HeatmapConfig()

        df = self.df.copy()

        # Filter by DTE
        df = df[(df["dte"] >= config.min_dte) & (df["dte"] <= config.max_dte)]

        if config.y_axis_mode == YAxisMode.MONEYNESS:
            df = df[
                (df["moneyness"] >= config.min_moneyness)
                & (df["moneyness"] <= config.max_moneyness)
            ]

        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for the specified filters",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
            return fig

        # Split by option type
        calls_df = df[df["option_type"] == "call"].copy()
        puts_df = df[df["option_type"] == "put"].copy()

        # Create subplots
        fig = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=("CALLS", "PUTS"),
            horizontal_spacing=0.1,
        )

        for i, (subset_df, col) in enumerate([(calls_df, 1), (puts_df, 2)], 1):
            if subset_df.empty:
                continue

            subset_df["y_value"] = self._get_y_values(subset_df, config.y_axis_mode)
            subset_df["z_value"] = self._get_z_values(subset_df, config.value_mode)

            pivot_df = subset_df.pivot_table(
                values="z_value",
                index="y_value",
                columns="dte",
                aggfunc="sum",
                fill_value=0,
            )

            pivot_df = pivot_df.sort_index(ascending=True)

            fig.add_trace(
                go.Heatmap(
                    z=pivot_df.values,
                    x=pivot_df.columns.tolist(),
                    y=pivot_df.index.tolist(),
                    colorscale=config.colorscale,
                    showscale=(col == 2),  # Only show colorbar on right
                    colorbar=dict(
                        title=self._get_colorbar_title(config.value_mode),
                    ),
                    hovertemplate=(
                        f"DTE: %{{x}}<br>"
                        f"{self._get_y_axis_title(config.y_axis_mode)}: %{{y:.2f}}<br>"
                        f"{self._get_colorbar_title(config.value_mode)}: %{{z:,.0f}}"
                        "<extra></extra>"
                    ),
                ),
                row=1,
                col=col,
            )

        # Set title
        if config.title:
            title = config.title
        else:
            title = (
                f"{self.chain_data.underlying_symbol} Options Liquidity - Calls vs Puts<br>"
                f"<sub>Underlying: ${self.chain_data.underlying_price:.2f} | "
                f"As of: {self.chain_data.fetch_timestamp.strftime('%Y-%m-%d %H:%M:%S')}</sub>"
            )

        # Update layout
        fig.update_layout(
            title=dict(text=title, x=0.5),
            height=config.height,
            width=config.width,
            template="plotly_dark",
        )

        # Update axes
        fig.update_xaxes(title_text="Days to Expiration (DTE)")
        fig.update_yaxes(title_text=self._get_y_axis_title(config.y_axis_mode))

        return fig

    def save_figure(
        self,
        fig: go.Figure,
        filepath: str,
        format: Literal["html", "png", "svg", "pdf", "json"] = "html",
    ) -> str:
        """
        Save a figure to file.

        Args:
            fig: Plotly Figure object
            filepath: Output file path (without extension)
            format: Output format. Defaults to "html".

        Returns:
            Full path to saved file
        """
        full_path = f"{filepath}.{format}"

        if format == "html":
            fig.write_html(full_path)
        elif format == "json":
            fig.write_json(full_path)
        else:
            # PNG, SVG, PDF require kaleido
            fig.write_image(full_path)

        return full_path

    def get_liquidity_summary(self) -> dict:
        """
        Get a summary of liquidity metrics.

        Returns:
            Dictionary with liquidity statistics
        """
        df = self.df

        return {
            "ticker": self.chain_data.underlying_symbol,
            "underlying_price": self.chain_data.underlying_price,
            "fetch_timestamp": self.chain_data.fetch_timestamp.isoformat(),
            "total_contracts": len(df),
            "total_open_interest": int(df["open_interest"].sum()),
            "total_volume": int(df["volume"].sum()),
            "calls": {
                "count": len(df[df["option_type"] == "call"]),
                "open_interest": int(df[df["option_type"] == "call"]["open_interest"].sum()),
                "volume": int(df[df["option_type"] == "call"]["volume"].sum()),
            },
            "puts": {
                "count": len(df[df["option_type"] == "put"]),
                "open_interest": int(df[df["option_type"] == "put"]["open_interest"].sum()),
                "volume": int(df[df["option_type"] == "put"]["volume"].sum()),
            },
            "expirations": len(df["expiration"].unique()),
            "strikes": len(df["strike"].unique()),
            "dte_range": {
                "min": int(df["dte"].min()),
                "max": int(df["dte"].max()),
            },
            "moneyness_range": {
                "min": float(df["moneyness"].min()),
                "max": float(df["moneyness"].max()),
            },
        }
