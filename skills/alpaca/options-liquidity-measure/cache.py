"""
Data caching utility for options chain data.

Saves data in: data/{{ticker}}/yyyy-mm-dd-HH-MM-ss/
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import OptionContract, OptionsChainData


class DataCache:
    """Cache manager for options chain data."""

    def __init__(self, base_dir: str = "data") -> None:
        """
        Initialize the cache manager.

        Args:
            base_dir: Base directory for cached data. Defaults to "data".
        """
        self.base_dir = Path(base_dir)

    def _get_cache_path(self, ticker: str, timestamp: datetime) -> Path:
        """
        Generate cache path for given ticker and timestamp.

        Format: data/{{ticker}}/yyyy-mm-dd-HH-MM-ss/

        Args:
            ticker: Stock ticker symbol
            timestamp: Timestamp for the cache entry

        Returns:
            Path object for the cache directory
        """
        time_str = timestamp.strftime("%Y-%m-%d-%H-%M-%S")
        return self.base_dir / ticker.upper() / time_str

    def _serialize_contract(self, contract: OptionContract) -> dict[str, Any]:
        """Serialize an OptionContract to dict."""
        return {
            "symbol": contract.symbol,
            "underlying_symbol": contract.underlying_symbol,
            "expiration_date": contract.expiration_date.isoformat(),
            "strike_price": contract.strike_price,
            "option_type": contract.option_type,
            "open_interest": contract.open_interest,
            "volume": contract.volume,
            "bid": contract.bid,
            "ask": contract.ask,
            "last_price": contract.last_price,
            "delta": contract.delta,
            "gamma": contract.gamma,
            "theta": contract.theta,
            "vega": contract.vega,
            "implied_volatility": contract.implied_volatility,
        }

    def _deserialize_contract(self, data: dict[str, Any]) -> OptionContract:
        """Deserialize a dict to OptionContract."""
        return OptionContract(
            symbol=data["symbol"],
            underlying_symbol=data["underlying_symbol"],
            expiration_date=datetime.fromisoformat(data["expiration_date"]),
            strike_price=data["strike_price"],
            option_type=data["option_type"],
            open_interest=data["open_interest"],
            volume=data["volume"],
            bid=data["bid"],
            ask=data["ask"],
            last_price=data["last_price"],
            delta=data.get("delta"),
            gamma=data.get("gamma"),
            theta=data.get("theta"),
            vega=data.get("vega"),
            implied_volatility=data.get("implied_volatility"),
        )

    def _serialize_chain(self, chain: OptionsChainData) -> dict[str, Any]:
        """Serialize OptionsChainData to dict."""
        return {
            "underlying_symbol": chain.underlying_symbol,
            "underlying_price": chain.underlying_price,
            "fetch_timestamp": chain.fetch_timestamp.isoformat(),
            "contracts": [self._serialize_contract(c) for c in chain.contracts],
        }

    def _deserialize_chain(self, data: dict[str, Any]) -> OptionsChainData:
        """Deserialize dict to OptionsChainData."""
        return OptionsChainData(
            underlying_symbol=data["underlying_symbol"],
            underlying_price=data["underlying_price"],
            fetch_timestamp=datetime.fromisoformat(data["fetch_timestamp"]),
            contracts=[self._deserialize_contract(c) for c in data["contracts"]],
        )

    def save(self, chain: OptionsChainData) -> Path:
        """
        Save options chain data to cache.

        Args:
            chain: Options chain data to save

        Returns:
            Path where data was saved
        """
        cache_path = self._get_cache_path(
            chain.underlying_symbol, chain.fetch_timestamp
        )
        cache_path.mkdir(parents=True, exist_ok=True)

        # Save as JSON
        data_file = cache_path / "options_chain.json"
        with open(data_file, "w") as f:
            json.dump(self._serialize_chain(chain), f, indent=2)

        # Save metadata
        metadata_file = cache_path / "metadata.json"
        metadata = {
            "ticker": chain.underlying_symbol,
            "underlying_price": chain.underlying_price,
            "fetch_timestamp": chain.fetch_timestamp.isoformat(),
            "total_contracts": len(chain.contracts),
            "expirations_count": len(chain.expirations),
            "strikes_count": len(chain.strikes),
            "calls_count": len(chain.calls),
            "puts_count": len(chain.puts),
        }
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        return cache_path

    def load(self, ticker: str, timestamp: datetime) -> OptionsChainData | None:
        """
        Load options chain data from cache.

        Args:
            ticker: Stock ticker symbol
            timestamp: Timestamp of the cache entry

        Returns:
            OptionsChainData if found, None otherwise
        """
        cache_path = self._get_cache_path(ticker, timestamp)
        data_file = cache_path / "options_chain.json"

        if not data_file.exists():
            return None

        with open(data_file) as f:
            data = json.load(f)

        return self._deserialize_chain(data)

    def load_latest(self, ticker: str) -> OptionsChainData | None:
        """
        Load the most recent cached data for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            OptionsChainData if found, None otherwise
        """
        ticker_dir = self.base_dir / ticker.upper()
        if not ticker_dir.exists():
            return None

        # Get all timestamp directories, sorted descending
        cache_dirs = sorted(ticker_dir.iterdir(), reverse=True)
        if not cache_dirs:
            return None

        # Try to load from the most recent
        for cache_dir in cache_dirs:
            data_file = cache_dir / "options_chain.json"
            if data_file.exists():
                with open(data_file) as f:
                    data = json.load(f)
                return self._deserialize_chain(data)

        return None

    def list_cached(self, ticker: str) -> list[datetime]:
        """
        List all cached timestamps for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of datetime objects for cached entries
        """
        ticker_dir = self.base_dir / ticker.upper()
        if not ticker_dir.exists():
            return []

        timestamps = []
        for cache_dir in ticker_dir.iterdir():
            if cache_dir.is_dir():
                try:
                    ts = datetime.strptime(cache_dir.name, "%Y-%m-%d-%H-%M-%S")
                    timestamps.append(ts)
                except ValueError:
                    continue

        return sorted(timestamps, reverse=True)

    def get_cache_size(self, ticker: str | None = None) -> int:
        """
        Get total cache size in bytes.

        Args:
            ticker: Optional ticker to filter by

        Returns:
            Total size in bytes
        """
        if ticker:
            search_dir = self.base_dir / ticker.upper()
        else:
            search_dir = self.base_dir

        if not search_dir.exists():
            return 0

        total_size = 0
        for dirpath, _, filenames in os.walk(search_dir):
            for filename in filenames:
                filepath = Path(dirpath) / filename
                total_size += filepath.stat().st_size

        return total_size

    def clear_cache(self, ticker: str | None = None, older_than: datetime | None = None) -> int:
        """
        Clear cached data.

        Args:
            ticker: Optional ticker to filter by
            older_than: Optional datetime to clear entries older than

        Returns:
            Number of entries cleared
        """
        import shutil

        if ticker:
            search_dir = self.base_dir / ticker.upper()
        else:
            search_dir = self.base_dir

        if not search_dir.exists():
            return 0

        cleared = 0

        if ticker:
            # Clear specific ticker
            for cache_dir in list(search_dir.iterdir()):
                if not cache_dir.is_dir():
                    continue

                should_clear = True
                if older_than:
                    try:
                        ts = datetime.strptime(cache_dir.name, "%Y-%m-%d-%H-%M-%S")
                        should_clear = ts < older_than
                    except ValueError:
                        should_clear = False

                if should_clear:
                    shutil.rmtree(cache_dir)
                    cleared += 1
        else:
            # Clear all tickers
            for ticker_dir in list(search_dir.iterdir()):
                if not ticker_dir.is_dir():
                    continue

                for cache_dir in list(ticker_dir.iterdir()):
                    if not cache_dir.is_dir():
                        continue

                    should_clear = True
                    if older_than:
                        try:
                            ts = datetime.strptime(cache_dir.name, "%Y-%m-%d-%H-%M-%S")
                            should_clear = ts < older_than
                        except ValueError:
                            should_clear = False

                    if should_clear:
                        shutil.rmtree(cache_dir)
                        cleared += 1

        return cleared
