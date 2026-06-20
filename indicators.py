from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Return"] = out["Close"].pct_change()
    out["SMA20"] = out["Close"].rolling(20).mean()
    out["SMA50"] = out["Close"].rolling(50).mean()
    out["SMA200"] = out["Close"].rolling(200).mean()
    out["EMA12"] = out["Close"].ewm(span=12, adjust=False).mean()
    out["EMA26"] = out["Close"].ewm(span=26, adjust=False).mean()
    out["MACD"] = out["EMA12"] - out["EMA26"]
    out["MACDSignal"] = out["MACD"].ewm(span=9, adjust=False).mean()
    out["RSI"] = rsi(out["Close"])
    out["ATR"] = atr(out)
    out["VolAvg20"] = out["Volume"].rolling(20).mean()
    out["Turnover"] = out["Close"] * out["Volume"]
    return out


def beta_alpha(stock: pd.DataFrame, benchmark: pd.DataFrame) -> tuple[float, float]:
    joined = pd.DataFrame({
        "stock": stock["Close"].pct_change(),
        "bench": benchmark["Close"].pct_change(),
    }).dropna()
    if len(joined) < 40 or joined["bench"].var() == 0:
        return 0.0, 0.0
    beta = float(joined["stock"].cov(joined["bench"]) / joined["bench"].var())
    daily_alpha = float(joined["stock"].mean() - beta * joined["bench"].mean())
    return beta, daily_alpha * 252 * 100


def support_resistance(df: pd.DataFrame, lookback: int = 60) -> tuple[float, float]:
    recent = df.tail(lookback)
    return float(recent["Low"].min()), float(recent["High"].max())
