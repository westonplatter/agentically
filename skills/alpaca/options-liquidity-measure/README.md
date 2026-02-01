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

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Set your Alpaca API credentials as environment variables:

```bash
export ALPACA_API_KEY="your-api-key"
export ALPACA_SECRET_KEY="your-secret-key"
export ALPACA_PAPER="true"  # Optional, defaults to true
```

## Usage

### Command Line

```bash
# Basic usage - generates a heatmap for AAPL
python -m skills.alpaca.options-liquidity-measure.cli AAPL

# Use moneyness on Y-axis with OI percentage
python -m skills.alpaca.options-liquidity-measure.cli SPY --y-axis moneyness --value oi_percent

# Create 3D surface plot for calls only
python -m skills.alpaca.options-liquidity-measure.cli QQQ --plot-type 3d --option-type call

# Filter by DTE range and show summary
python -m skills.alpaca.options-liquidity-measure.cli TSLA --dte-min 7 --dte-max 45 --summary

# Save as PNG and open in browser
python -m skills.alpaca.options-liquidity-measure.cli NVDA --format png --show
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

# Get summary statistics
summary = heatmap.get_liquidity_summary()
print(f"Total OI: {summary['total_open_interest']:,}")
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
| `--value` | `oi_absolute` | Value mode: `oi_absolute`, `oi_percent`, `volume_absolute`, `volume_percent` |
| `--option-type` | `both` | Filter: `call`, `put`, `both` |
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
