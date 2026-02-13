"""
Options chain data fetcher using Alpaca's official Python SDK.

Requires environment variables:
- ALPACA_API_KEY: Your Alpaca API key
- ALPACA_SECRET_KEY: Your Alpaca secret key

Optional:
- ALPACA_PAPER: Set to "true" for paper trading (default: true)
"""

import os
from datetime import datetime, timedelta
from typing import Literal

from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest, OptionSnapshotRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOptionContractsRequest
from alpaca.data.models import OptionSnapshot

from .cache import DataCache
from .models import OptionContract, OptionsChainData


class OptionsChainFetcher:
    """Fetches options chain data from Alpaca API."""

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        paper: bool = True,
        cache_dir: str = "data",
        auto_cache: bool = True,
    ) -> None:
        """
        Initialize the options chain fetcher.

        Args:
            api_key: Alpaca API key. Defaults to ALPACA_API_KEY env var.
            secret_key: Alpaca secret key. Defaults to ALPACA_SECRET_KEY env var.
            paper: Use paper trading API. Defaults to True.
            cache_dir: Directory for caching data. Defaults to "data".
            auto_cache: Automatically cache fetched data. Defaults to True.
        """
        self.api_key = api_key or os.environ.get("ALPACA_API_KEY")
        self.secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY")

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Alpaca API credentials required. "
                "Set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables, "
                "or pass api_key and secret_key parameters."
            )

        # Check for paper trading env var
        paper_env = os.environ.get("ALPACA_PAPER", "true").lower()
        if paper_env in ("false", "0", "no"):
            paper = False

        self.paper = paper
        self.auto_cache = auto_cache
        self.cache = DataCache(base_dir=cache_dir)

        # Initialize Alpaca clients
        self.trading_client = TradingClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=self.paper,
        )

        self.option_data_client = OptionHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
        )

    def _get_underlying_price(self, symbol: str) -> float:
        """
        Get the current price of the underlying asset.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Current price as float
        """
        from alpaca.data.historical.stock import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestQuoteRequest

        stock_client = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
        )

        request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        quotes = stock_client.get_stock_latest_quote(request)

        if symbol in quotes:
            quote = quotes[symbol]
            # Use midpoint of bid/ask
            return (quote.bid_price + quote.ask_price) / 2

        raise ValueError(f"Could not get quote for {symbol}")

    def fetch(
        self,
        symbol: str,
        min_dte: int = 0,
        max_dte: int = 90,
        option_type: Literal["call", "put", "both"] = "both",
        min_strike: float | None = None,
        max_strike: float | None = None,
        moneyness_range: tuple[float, float] | None = None,
    ) -> OptionsChainData:
        """
        Fetch options chain data from Alpaca.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "SPY")
            min_dte: Minimum days to expiration. Defaults to 0.
            max_dte: Maximum days to expiration. Defaults to 90.
            option_type: Filter by option type. Defaults to "both".
            min_strike: Minimum strike price filter.
            max_strike: Maximum strike price filter.
            moneyness_range: Filter by moneyness (min, max). E.g., (0.8, 1.2).

        Returns:
            OptionsChainData containing the fetched contracts
        """
        fetch_timestamp = datetime.now()
        symbol = symbol.upper()

        # Get underlying price first
        underlying_price = self._get_underlying_price(symbol)

        # Calculate strike range from moneyness if provided
        if moneyness_range:
            min_moneyness, max_moneyness = moneyness_range
            min_strike = underlying_price * min_moneyness
            max_strike = underlying_price * max_moneyness

        # Calculate expiration date range
        today = datetime.now().date()
        min_expiration = today + timedelta(days=min_dte)
        max_expiration = today + timedelta(days=max_dte)

        # Build option contracts request
        request_params: dict = {
            "underlying_symbols": [symbol],
            "expiration_date_gte": min_expiration,
            "expiration_date_lte": max_expiration,
        }

        if option_type != "both":
            request_params["type"] = option_type

        if min_strike is not None:
            request_params["strike_price_gte"] = min_strike

        if max_strike is not None:
            request_params["strike_price_lte"] = max_strike

        request = GetOptionContractsRequest(**request_params)

        # Fetch option contracts list
        contracts_response = self.trading_client.get_option_contracts(request)

        if not contracts_response or not contracts_response.option_contracts:
            return OptionsChainData(
                underlying_symbol=symbol,
                underlying_price=underlying_price,
                fetch_timestamp=fetch_timestamp,
                contracts=[],
            )

        # Get option symbols for snapshot request
        option_symbols = [c.symbol for c in contracts_response.option_contracts]

        # Fetch snapshots for all options (includes greeks, OI, volume)
        contracts: list[OptionContract] = []

        # Process in batches (Alpaca may have limits)
        batch_size = 100
        for i in range(0, len(option_symbols), batch_size):
            batch_symbols = option_symbols[i : i + batch_size]

            try:
                snapshot_request = OptionSnapshotRequest(symbol_or_symbols=batch_symbols)
                snapshots = self.option_data_client.get_option_snapshot(snapshot_request)

                for occ_symbol, snapshot in snapshots.items():
                    contract = self._parse_snapshot(occ_symbol, symbol, snapshot)
                    if contract:
                        contracts.append(contract)

            except Exception as e:
                # Log but continue with remaining batches
                print(f"Warning: Failed to fetch batch {i//batch_size + 1}: {e}")
                continue

        chain_data = OptionsChainData(
            underlying_symbol=symbol,
            underlying_price=underlying_price,
            fetch_timestamp=fetch_timestamp,
            contracts=contracts,
        )

        # Auto-cache if enabled
        if self.auto_cache:
            self.cache.save(chain_data)

        return chain_data

    def _parse_snapshot(
        self,
        occ_symbol: str,
        underlying: str,
        snapshot: OptionSnapshot,
    ) -> OptionContract | None:
        """
        Parse an Alpaca OptionSnapshot into our OptionContract model.

        Args:
            occ_symbol: OCC option symbol
            underlying: Underlying stock symbol
            snapshot: Alpaca OptionSnapshot object

        Returns:
            OptionContract or None if parsing fails
        """
        try:
            # Parse OCC symbol format: AAPL230616C00150000
            # Format: SYMBOL + YYMMDD + C/P + STRIKE (8 digits, strike * 1000)
            symbol_part = occ_symbol[:-15]  # Everything except last 15 chars
            date_part = occ_symbol[-15:-9]  # 6 chars for YYMMDD
            type_char = occ_symbol[-9]  # C or P
            strike_part = occ_symbol[-8:]  # 8 digits for strike

            exp_date = datetime.strptime(date_part, "%y%m%d")
            option_type: Literal["call", "put"] = "call" if type_char == "C" else "put"
            strike_price = int(strike_part) / 1000

            # Extract data from snapshot
            quote = snapshot.latest_quote
            trade = snapshot.latest_trade
            greeks = snapshot.greeks

            bid = quote.bid_price if quote else 0.0
            ask = quote.ask_price if quote else 0.0
            last_price = trade.price if trade else 0.0

            # Open interest and volume from daily bars or implied
            open_interest = snapshot.open_interest if hasattr(snapshot, 'open_interest') else 0
            volume = snapshot.daily_bar.volume if snapshot.daily_bar else 0

            # Greeks
            delta = greeks.delta if greeks else None
            gamma = greeks.gamma if greeks else None
            theta = greeks.theta if greeks else None
            vega = greeks.vega if greeks else None

            # Implied volatility
            iv = snapshot.implied_volatility if hasattr(snapshot, 'implied_volatility') else None

            return OptionContract(
                symbol=occ_symbol,
                underlying_symbol=underlying,
                expiration_date=exp_date,
                strike_price=strike_price,
                option_type=option_type,
                open_interest=open_interest or 0,
                volume=volume or 0,
                bid=bid,
                ask=ask,
                last_price=last_price,
                delta=delta,
                gamma=gamma,
                theta=theta,
                vega=vega,
                implied_volatility=iv,
            )

        except Exception as e:
            print(f"Warning: Failed to parse option {occ_symbol}: {e}")
            return None

    def fetch_cached_or_live(
        self,
        symbol: str,
        max_age_minutes: int = 15,
        **fetch_kwargs,
    ) -> OptionsChainData:
        """
        Fetch from cache if recent, otherwise fetch live data.

        Args:
            symbol: Stock ticker symbol
            max_age_minutes: Max age of cached data in minutes. Defaults to 15.
            **fetch_kwargs: Additional arguments for fetch()

        Returns:
            OptionsChainData from cache or live fetch
        """
        cached = self.cache.load_latest(symbol)

        if cached:
            age = datetime.now() - cached.fetch_timestamp
            if age.total_seconds() < max_age_minutes * 60:
                return cached

        return self.fetch(symbol, **fetch_kwargs)
