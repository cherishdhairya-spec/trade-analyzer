from __future__ import annotations

from functools import lru_cache

import pandas as pd
import yfinance as yf


def yf_symbol(symbol: str) -> str:
    symbol = symbol.upper()
    return symbol if symbol.endswith(".NS") or symbol.startswith("^") else f"{symbol}.NS"


def fetch_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    data = yf.download(
        yf_symbol(symbol),
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False,
        threads=False,
    )
    if data.empty:
        return data
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data.rename(columns=str.title)
    data = data.dropna(subset=["Open", "High", "Low", "Close"])
    data.index = pd.to_datetime(data.index)
    return data


@lru_cache(maxsize=512)
def fetch_info(symbol: str) -> dict:
    try:
        return yf.Ticker(yf_symbol(symbol)).get_info() or {}
    except Exception:
        return {}


@lru_cache(maxsize=8)
def fetch_benchmark(period: str = "1y") -> pd.DataFrame:
    return fetch_history("^NSEI", period=period, interval="1d")
