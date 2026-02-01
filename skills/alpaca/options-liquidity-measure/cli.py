#!/usr/bin/env python3
"""
CLI entry point for options liquidity heatmap generation.

Usage:
    python -m skills.alpaca.options-liquidity-measure.cli AAPL --dte-max 60
    python cli.py SPY --y-axis moneyness --value volume_percent --output spy_liquidity
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .fetcher import OptionsChainFetcher
from .heatmap import LiquidityHeatmap
from .models import HeatmapConfig, YAxisMode, ValueMode


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate options chain liquidity heatmaps using Alpaca data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s AAPL
  %(prog)s SPY --y-axis moneyness --value oi_percent
  %(prog)s QQQ --dte-min 7 --dte-max 45 --plot-type 3d
  %(prog)s TSLA --option-type call --output tsla_calls
  %(prog)s NVDA --value spread_percent --y-axis moneyness  # Bid-ask spread heatmap
  %(prog)s AMD --value spread_absolute --summary  # Show spread statistics

Environment Variables:
  ALPACA_API_KEY      Your Alpaca API key (required)
  ALPACA_SECRET_KEY   Your Alpaca secret key (required)
  ALPACA_PAPER        Set to 'false' for live trading (default: true)
        """,
    )

    parser.add_argument(
        "ticker",
        type=str,
        help="Stock ticker symbol (e.g., AAPL, SPY, QQQ)",
    )

    parser.add_argument(
        "--y-axis",
        type=str,
        choices=["strike", "moneyness", "delta"],
        default="strike",
        help="Y-axis mode (default: strike)",
    )

    parser.add_argument(
        "--value",
        type=str,
        choices=[
            "oi_absolute", "oi_percent",
            "volume_absolute", "volume_percent",
            "spread_absolute", "spread_percent", "spread_per_delta",
        ],
        default="oi_absolute",
        help="Value mode for heatmap bins. Liquidity: oi_*, volume_*. "
             "Spread: spread_absolute ($), spread_percent (%%), spread_per_delta. "
             "(default: oi_absolute)",
    )

    parser.add_argument(
        "--option-type",
        type=str,
        choices=["call", "put", "both"],
        default="both",
        help="Option type filter (default: both)",
    )

    parser.add_argument(
        "--dte-min",
        type=int,
        default=0,
        help="Minimum days to expiration (default: 0)",
    )

    parser.add_argument(
        "--dte-max",
        type=int,
        default=90,
        help="Maximum days to expiration (default: 90)",
    )

    parser.add_argument(
        "--moneyness-min",
        type=float,
        default=0.8,
        help="Minimum moneyness filter (default: 0.8)",
    )

    parser.add_argument(
        "--moneyness-max",
        type=float,
        default=1.2,
        help="Maximum moneyness filter (default: 1.2)",
    )

    parser.add_argument(
        "--plot-type",
        type=str,
        choices=["heatmap", "3d", "split"],
        default="heatmap",
        help="Plot type: heatmap, 3d surface, or split calls/puts (default: heatmap)",
    )

    parser.add_argument(
        "--colorscale",
        type=str,
        default="Viridis",
        help="Plotly colorscale (default: Viridis)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output filename (without extension). Defaults to {ticker}_liquidity",
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["html", "png", "svg", "pdf"],
        default="html",
        help="Output format (default: html)",
    )

    parser.add_argument(
        "--cache-dir",
        type=str,
        default="data",
        help="Directory for cached data (default: data)",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable data caching",
    )

    parser.add_argument(
        "--use-cached",
        action="store_true",
        help="Use cached data if available (max 15 min old)",
    )

    parser.add_argument(
        "--show",
        action="store_true",
        help="Open the plot in browser after saving",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print liquidity summary statistics",
    )

    parser.add_argument(
        "--width",
        type=int,
        default=1200,
        help="Figure width in pixels (default: 1200)",
    )

    parser.add_argument(
        "--height",
        type=int,
        default=800,
        help="Figure height in pixels (default: 800)",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    print(f"Fetching options chain for {args.ticker}...")

    try:
        # Initialize fetcher
        fetcher = OptionsChainFetcher(
            cache_dir=args.cache_dir,
            auto_cache=not args.no_cache,
        )

        # Fetch data
        if args.use_cached:
            chain_data = fetcher.fetch_cached_or_live(
                symbol=args.ticker,
                min_dte=args.dte_min,
                max_dte=args.dte_max,
                option_type=args.option_type,
                moneyness_range=(args.moneyness_min, args.moneyness_max),
            )
        else:
            chain_data = fetcher.fetch(
                symbol=args.ticker,
                min_dte=args.dte_min,
                max_dte=args.dte_max,
                option_type=args.option_type,
                moneyness_range=(args.moneyness_min, args.moneyness_max),
            )

        print(f"Fetched {len(chain_data.contracts)} contracts")
        print(f"Underlying price: ${chain_data.underlying_price:.2f}")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        return 1

    # Create heatmap generator
    heatmap = LiquidityHeatmap(chain_data)

    # Print summary if requested
    if args.summary:
        summary = heatmap.get_liquidity_summary()
        print("\n=== Liquidity Summary ===")
        print(f"Total Contracts: {summary['total_contracts']}")
        print(f"Total Open Interest: {summary['total_open_interest']:,}")
        print(f"Total Volume: {summary['total_volume']:,}")
        print(f"Calls: {summary['calls']['count']} contracts, "
              f"OI: {summary['calls']['open_interest']:,}, "
              f"Vol: {summary['calls']['volume']:,}")
        print(f"Puts: {summary['puts']['count']} contracts, "
              f"OI: {summary['puts']['open_interest']:,}, "
              f"Vol: {summary['puts']['volume']:,}")
        print(f"Expirations: {summary['expirations']}")
        print(f"Strikes: {summary['strikes']}")
        print(f"DTE Range: {summary['dte_range']['min']} - {summary['dte_range']['max']}")
        print(f"Moneyness Range: {summary['moneyness_range']['min']:.2f} - "
              f"{summary['moneyness_range']['max']:.2f}")

        # Spread statistics
        spread_stats = summary.get("spread_stats", {})
        if spread_stats.get("contracts_with_quotes", 0) > 0:
            print("\n=== Bid-Ask Spread Statistics ===")
            print(f"Contracts with quotes: {spread_stats['contracts_with_quotes']}")
            print(f"Avg Spread: ${spread_stats['avg_spread_absolute']:.2f} "
                  f"({spread_stats['avg_spread_percent']:.1f}%)")
            print(f"Median Spread: ${spread_stats['median_spread_absolute']:.2f} "
                  f"({spread_stats['median_spread_percent']:.1f}%)")
            print(f"Range: ${spread_stats['min_spread_absolute']:.2f} - "
                  f"${spread_stats['max_spread_absolute']:.2f}")

            if spread_stats.get("tightest_spread_contracts"):
                print("\nTightest Spreads:")
                for contract in spread_stats["tightest_spread_contracts"]:
                    print(f"  {contract['option_type'].upper()} {contract['strike']} "
                          f"(DTE {contract['dte']}): "
                          f"${contract['spread_absolute']:.2f} ({contract['spread_percent']:.1f}%) "
                          f"[{contract['bid']:.2f} x {contract['ask']:.2f}]")
        print()

    # Build config
    y_axis_map = {
        "strike": YAxisMode.STRIKE,
        "moneyness": YAxisMode.MONEYNESS,
        "delta": YAxisMode.DELTA,
    }

    value_map = {
        "oi_absolute": ValueMode.OPEN_INTEREST_ABSOLUTE,
        "oi_percent": ValueMode.OPEN_INTEREST_PERCENT,
        "volume_absolute": ValueMode.VOLUME_ABSOLUTE,
        "volume_percent": ValueMode.VOLUME_PERCENT,
        "spread_absolute": ValueMode.SPREAD_ABSOLUTE,
        "spread_percent": ValueMode.SPREAD_PERCENT,
        "spread_per_delta": ValueMode.SPREAD_PER_DELTA,
    }

    config = HeatmapConfig(
        y_axis_mode=y_axis_map[args.y_axis],
        value_mode=value_map[args.value],
        option_type=args.option_type,
        min_dte=args.dte_min,
        max_dte=args.dte_max,
        min_moneyness=args.moneyness_min,
        max_moneyness=args.moneyness_max,
        colorscale=args.colorscale,
        height=args.height,
        width=args.width,
    )

    # Create figure
    print(f"Creating {args.plot_type} visualization...")

    if args.plot_type == "heatmap":
        fig = heatmap.create_heatmap(config)
    elif args.plot_type == "3d":
        fig = heatmap.create_3d_surface(config)
    elif args.plot_type == "split":
        fig = heatmap.create_split_heatmap(config)
    else:
        print(f"Unknown plot type: {args.plot_type}", file=sys.stderr)
        return 1

    # Determine output filename
    if args.output:
        output_name = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"{args.ticker.lower()}_liquidity_{timestamp}"

    # Ensure output directory exists
    output_path = Path(output_name)
    if output_path.parent != Path("."):
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save figure
    full_path = heatmap.save_figure(fig, str(output_path), args.format)
    print(f"Saved: {full_path}")

    # Open in browser if requested
    if args.show:
        if args.format == "html":
            import webbrowser
            webbrowser.open(f"file://{Path(full_path).absolute()}")
        else:
            fig.show()

    return 0


if __name__ == "__main__":
    sys.exit(main())
