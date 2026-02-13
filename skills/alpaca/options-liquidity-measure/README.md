# Options Liquidity Heatmap

A skill for visualizing options chain liquidity using 3D heatmaps. Uses Alpaca's official Python SDK for real-time options data.

## Features

- **Real-time data**: Fetches live options chain data from Alpaca
- **Data caching**: Saves fetched data locally for later analysis
- **Multiple visualization modes**:
  - 2D Heatmap
  - 3D Surface plot
  - Split calls/puts comparison
- **Flexible Y-axis options**:
  - Strike price (absolute)
  - Moneyness (strike/underlying)
  - Delta
- **Multiple value metrics**:
  - Open Interest (absolute)
  - Open Interest (% of DTE total)
  - Volume (absolute)
  - Volume (% of DTE total)
- **Bid-Ask Spread Analysis**:
  - Spread in dollars (absolute)
  - Spread as % of mid price
  - Spread per delta (cost of delta exposure)
  - Color-coded: green = tight spreads (good), red = wide spreads (poor liquidity)

## Installation

```bash
uv pip install -r requirements.txt
```

Or let `uv` handle dependencies automatically when running commands.

## Configuration

Set your Alpaca API credentials as environment variables:

```bash
export ALPACA_API_KEY="your-api-key"
export ALPACA_SECRET_KEY="your-secret-key"
export ALPACA_PAPER="true"  # Optional, defaults to true
```

## Usage

export OPENAI_API_KEY=$(op read "op://sts_llm/mp_openai/api_key")                                                                                      
  uv run python scripts/chunk_ingest.py \
      --doc-type tech_tip \
      --table-config openai_chunk500 \
      --chunk-size 500 \
      --chunk-overlap 50 \
      --batch-size 32

### Command Line

```bash
# Basic usage - generates a heatmap for AAPL
uv run python -m skills.alpaca.options-liquidity-measure.cli AAPL

# Use moneyness on Y-axis with OI percentage
uv run python -m skills.alpaca.options-liquidity-measure.cli SPY --y-axis moneyness --value oi_percent

# Create 3D surface plot for calls only
uv run python -m skills.alpaca.options-liquidity-measure.cli QQQ --plot-type 3d --option-type call

# Filter by DTE range and show summary
uv run python -m skills.alpaca.options-liquidity-measure.cli TSLA --dte-min 7 --dte-max 45 --summary

# Save as PNG and open in browser
uv run python -m skills.alpaca.options-liquidity-measure.cli NVDA --format png --show

# Bid-ask spread heatmap (% of mid price) - see where liquidity is best
uv run python -m skills.alpaca.options-liquidity-measure.cli SPY --value spread_percent --y-axis moneyness

# Absolute spread heatmap with summary statistics
uv run python -m skills.alpaca.options-liquidity-measure.cli AAPL --value spread_absolute --summary

# Spread per delta - cost efficiency for delta exposure
uv run python -m skills.alpaca.options-liquidity-measure.cli QQQ --value spread_per_delta --option-type call
```

### Python API

```python
from skills.alpaca.options_liquidity_measure import (
    OptionsChainFetcher,
    LiquidityHeatmap,
    HeatmapConfig,
    YAxisMode,
    ValueMode,
)

# Initialize fetcher (uses env vars for credentials)
fetcher = OptionsChainFetcher()

# Fetch options chain data
chain_data = fetcher.fetch(
    symbol="AAPL",
    min_dte=0,
    max_dte=60,
    moneyness_range=(0.9, 1.1),
)

# Create heatmap generator
heatmap = LiquidityHeatmap(chain_data)

# Configure visualization
config = HeatmapConfig(
    y_axis_mode=YAxisMode.MONEYNESS,
    value_mode=ValueMode.OPEN_INTEREST_PERCENT,
    option_type="both",
    colorscale="Viridis",
)

# Generate figures
fig_2d = heatmap.create_heatmap(config)
fig_3d = heatmap.create_3d_surface(config)
fig_split = heatmap.create_split_heatmap(config)

# Save or display
heatmap.save_figure(fig_2d, "aapl_liquidity", format="html")
fig_2d.show()  # Opens in browser

# Get summary statistics (includes spread stats)
summary = heatmap.get_liquidity_summary()
print(f"Total OI: {summary['total_open_interest']:,}")
print(f"Avg Spread: ${summary['spread_stats']['avg_spread_absolute']:.2f}")
print(f"Tightest spread: {summary['spread_stats']['tightest_spread_contracts'][0]}")

# Create bid-ask spread heatmap
spread_config = HeatmapConfig(
    y_axis_mode=YAxisMode.MONEYNESS,
    value_mode=ValueMode.SPREAD_PERCENT,  # Spread as % of mid price
    min_moneyness=0.95,
    max_moneyness=1.05,
)
spread_fig = heatmap.create_heatmap(spread_config)
spread_fig.show()  # Green = tight spreads, Red = wide spreads
```

### Using Cached Data

```python
# Load most recent cached data
from skills.alpaca.options_liquidity_measure import DataCache

cache = DataCache(base_dir="data")
chain_data = cache.load_latest("AAPL")

# List all cached timestamps
timestamps = cache.list_cached("AAPL")

# Use cached data if recent, otherwise fetch live
chain_data = fetcher.fetch_cached_or_live(
    symbol="AAPL",
    max_age_minutes=15,
)
```

## Data Caching

Fetched data is automatically cached in the following structure:

```
data/
  AAPL/
    2024-01-15-14-30-45/
      options_chain.json
      metadata.json
    2024-01-15-15-00-12/
      options_chain.json
      metadata.json
  SPY/
    ...
```

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--y-axis` | `strike` | Y-axis mode: `strike`, `moneyness`, `delta` |
| `--value` | `oi_absolute` | Value mode (see below) |
| `--option-type` | `both` | Filter: `call`, `put`, `both` |

### Value Modes

| Mode | Description |
|------|-------------|
| `oi_absolute` | Open Interest (raw count) |
| `oi_percent` | Open Interest as % of DTE total |
| `volume_absolute` | Volume (raw count) |
| `volume_percent` | Volume as % of DTE total |
| `spread_absolute` | Bid-ask spread in dollars |
| `spread_percent` | Bid-ask spread as % of mid price |
| `spread_per_delta` | Spread normalized by delta ($/delta) |

### Other Options
| `--dte-min` | `0` | Minimum days to expiration |
| `--dte-max` | `90` | Maximum days to expiration |
| `--moneyness-min` | `0.8` | Min moneyness filter |
| `--moneyness-max` | `1.2` | Max moneyness filter |
| `--plot-type` | `heatmap` | Plot type: `heatmap`, `3d`, `split` |
| `--colorscale` | `Viridis` | Plotly colorscale |
| `--output` | auto | Output filename |
| `--format` | `html` | Output format: `html`, `png`, `svg`, `pdf` |
| `--cache-dir` | `data` | Cache directory |
| `--no-cache` | - | Disable caching |
| `--use-cached` | - | Use cached data if available |
| `--show` | - | Open plot in browser |
| `--summary` | - | Print liquidity summary |

## Bid-Ask Spread Analysis

The spread heatmaps help traders identify where market liquidity is best (tight spreads) or worst (wide spreads) across the options chain.

### Interpreting Spread Heatmaps

- **Green zones**: Tight spreads = good liquidity, lower transaction costs
- **Red zones**: Wide spreads = poor liquidity, higher transaction costs
- **Colorscale is reversed** for spread metrics so that "better" (lower) values appear green

### Spread Metrics

| Metric | Use Case |
|--------|----------|
| `spread_absolute` | Raw dollar cost to cross the spread. Good for comparing similar-priced options. |
| `spread_percent` | Spread relative to option price. Better for comparing across different strikes/expirations. |
| `spread_per_delta` | Cost per unit of delta exposure. Useful for delta-neutral strategies to find the most efficient hedging instruments. |

### Tips

- ATM options typically have tighter spreads than deep OTM/ITM
- Near-term expirations often have better liquidity than far-dated
- High OI/volume doesn't always mean tight spreads - check both!
- Use `--summary` to see spread statistics including the tightest spread contracts

## Colorscales

Supported Plotly colorscales include:
- `Viridis` (default)
- `Plasma`
- `Inferno`
- `Magma`
- `Hot`
- `YlOrRd`
- `Blues`
- `Greens`
- `RdBu` (diverging)

## Requirements

- Python 3.10+
- Alpaca account with options data access
- See `requirements.txt` for dependencies
