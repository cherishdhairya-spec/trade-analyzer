from __future__ import annotations

import pandas as pd


def detect_patterns(df: pd.DataFrame) -> list[dict]:
    patterns: list[dict] = []
    if len(df) < 60:
        return patterns

    recent = df.tail(12)
    for idx, row in recent.iterrows():
        body = abs(row["Close"] - row["Open"])
        candle_range = max(row["High"] - row["Low"], 0.01)
        upper = row["High"] - max(row["Open"], row["Close"])
        lower = min(row["Open"], row["Close"]) - row["Low"]
        if body / candle_range < 0.12:
            patterns.append({"date": idx.strftime("%Y-%m-%d"), "name": "Doji", "price": float(row["Close"])})
        if lower > body * 2 and upper < body * 1.2 and row["Close"] > row["Open"]:
            patterns.append({"date": idx.strftime("%Y-%m-%d"), "name": "Hammer", "price": float(row["Low"])})

    last = df.iloc[-1]
    prev = df.iloc[-2]
    if (
        prev["Close"] < prev["Open"]
        and last["Close"] > last["Open"]
        and last["Close"] > prev["Open"]
        and last["Open"] < prev["Close"]
    ):
        patterns.append({"date": df.index[-1].strftime("%Y-%m-%d"), "name": "Bullish Engulfing", "price": float(last["Close"])})

    if df["SMA50"].iloc[-2] <= df["SMA200"].iloc[-2] and df["SMA50"].iloc[-1] > df["SMA200"].iloc[-1]:
        patterns.append({"date": df.index[-1].strftime("%Y-%m-%d"), "name": "Golden Cross", "price": float(last["Close"])})

    resistance = df["High"].tail(60).max()
    if last["Close"] >= resistance * 0.995 and last["Volume"] > df["VolAvg20"].iloc[-1] * 1.2:
        patterns.append({"date": df.index[-1].strftime("%Y-%m-%d"), "name": "Volume Breakout", "price": float(last["Close"])})

    lows = df["Low"].tail(45)
    first_low = lows.iloc[:22].min()
    second_low = lows.iloc[22:].min()
    if abs(first_low - second_low) / max(first_low, 1) < 0.03 and last["Close"] > df["Close"].tail(20).mean():
        patterns.append({"date": df.index[-1].strftime("%Y-%m-%d"), "name": "Possible Double Bottom", "price": float(last["Close"])})

    return patterns[-6:]
