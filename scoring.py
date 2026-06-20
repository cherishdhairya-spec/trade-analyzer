from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass

import numpy as np

from data_sources import fetch_benchmark, fetch_history, fetch_info
from indicators import add_indicators, beta_alpha, support_resistance
from patterns import detect_patterns
from universe import get_universe


PROFILE_RULES = {
    "less": {"max_beta": 1.05, "vol_penalty": 1.3, "reward_mult": 1.6},
    "moderate": {"max_beta": 1.35, "vol_penalty": 1.0, "reward_mult": 2.0},
    "high": {"max_beta": 2.0, "vol_penalty": 0.7, "reward_mult": 2.6},
}


@dataclass
class StockAnalysis:
    symbol: str
    name: str
    sector: str
    score: float
    action: str
    risk_category: str
    entry: float
    stoploss: float
    target: float
    reward_pct: float
    risk_pct: float
    pe_ratio: float
    market_cap: float
    turnover: float
    volatility: float
    std_dev: float
    alpha: float
    beta: float
    rsi: float
    patterns: list[dict]
    current_situation: str
    company_aim: str
    risks: str
    profit_case: str

    def to_record(self) -> dict:
        return asdict(self)


def _risk_category(beta: float, volatility: float, risk_pct: float) -> str:
    if beta <= 0.9 and volatility < 24 and risk_pct <= 6:
        return "less"
    if beta <= 1.35 and volatility < 38 and risk_pct <= 10:
        return "moderate"
    return "high"


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except Exception:
        return default


def analyze_symbol(symbol: str, profile: str = "moderate") -> StockAnalysis | None:
    df = fetch_history(symbol, period="1y")
    if len(df) < 220:
        return None
    df = add_indicators(df)
    bench = add_indicators(fetch_benchmark("1y"))
    beta, alpha = beta_alpha(df, bench)
    info = fetch_info(symbol)

    last = df.iloc[-1]
    close = _safe_float(last["Close"])
    atr = _safe_float(last.get("ATR"), close * 0.03)
    support, resistance = support_resistance(df)
    pe = _safe_float(info.get("trailingPE") or info.get("forwardPE"))
    market_cap = _safe_float(info.get("marketCap"))
    turnover = _safe_float(df["Turnover"].tail(20).mean())
    volatility = _safe_float(df["Return"].std() * np.sqrt(252) * 100)
    std_dev = _safe_float(df["Return"].std() * 100)
    rsi = _safe_float(last.get("RSI"), 50)
    patterns = detect_patterns(df)

    trend_score = 0
    trend_score += 18 if close > _safe_float(last["SMA200"], close) else -12
    trend_score += 14 if close > _safe_float(last["SMA50"], close) else -8
    trend_score += 8 if _safe_float(last["SMA50"], close) > _safe_float(last["SMA200"], close) else -6
    momentum_score = 12 if 45 <= rsi <= 68 else (-8 if rsi > 78 or rsi < 32 else 3)
    macd_score = 8 if _safe_float(last["MACD"]) > _safe_float(last["MACDSignal"]) else -4
    volume_score = 6 if _safe_float(last["Volume"]) > _safe_float(last["VolAvg20"]) else 0
    pattern_score = min(len(patterns) * 4, 16)
    fundamental_score = 0
    if 0 < pe < 45:
        fundamental_score += 10
    if market_cap > 500_000_000_000:
        fundamental_score += 8
    if turnover > 1_000_000_000:
        fundamental_score += 6

    rules = PROFILE_RULES.get(profile, PROFILE_RULES["moderate"])
    risk_penalty = max(volatility - 22, 0) * rules["vol_penalty"] / 3
    beta_penalty = max(beta - rules["max_beta"], 0) * 12
    score = trend_score + momentum_score + macd_score + volume_score + pattern_score + fundamental_score + alpha / 8 - risk_penalty - beta_penalty

    entry = close
    stoploss = max(close - max(atr * 1.8, close * 0.045), support * 0.985)
    target = close + (close - stoploss) * rules["reward_mult"]
    risk_pct = max((entry - stoploss) / entry * 100, 0)
    reward_pct = max((target - entry) / entry * 100, 0)
    risk_cat = _risk_category(beta, volatility, risk_pct)

    if score >= 45 and close > _safe_float(last["SMA50"], close) and risk_pct <= 16:
        action = "BUY WATCH"
    elif close < _safe_float(last["SMA50"], close) or rsi < 35:
        action = "AVOID/SELL"
    else:
        action = "HOLD WATCH"

    name = str(info.get("longName") or info.get("shortName") or symbol)
    sector = str(info.get("sector") or "Unknown")
    summary = str(info.get("longBusinessSummary") or "")
    company_aim = summary[:480] + ("..." if len(summary) > 480 else "")
    if not company_aim:
        company_aim = "Company description was not available from the data source."

    current = (
        f"Close {close:.2f}; RSI {rsi:.1f}; beta {beta:.2f}; "
        f"annual volatility {volatility:.1f}%; trend is "
        f"{'above' if close > _safe_float(last['SMA50'], close) else 'below'} the 50-day average."
    )
    risks = f"Estimated downside to stoploss is {risk_pct:.2f}%; beta {beta:.2f}; volatility {volatility:.1f}%."
    profit_case = f"Target gives estimated upside of {reward_pct:.2f}% if momentum and trend continue."

    return StockAnalysis(
        symbol=symbol,
        name=name,
        sector=sector,
        score=round(score, 2),
        action=action,
        risk_category=risk_cat,
        entry=round(entry, 2),
        stoploss=round(stoploss, 2),
        target=round(target, 2),
        reward_pct=round(reward_pct, 2),
        risk_pct=round(risk_pct, 2),
        pe_ratio=round(pe, 2),
        market_cap=round(market_cap, 2),
        turnover=round(turnover, 2),
        volatility=round(volatility, 2),
        std_dev=round(std_dev, 3),
        alpha=round(alpha, 2),
        beta=round(beta, 3),
        rsi=round(rsi, 2),
        patterns=patterns,
        current_situation=current,
        company_aim=company_aim,
        risks=risks,
        profit_case=profit_case,
    )


def run_scan(profile: str = "moderate", limit: int = 50) -> tuple[list[StockAnalysis], list[str]]:
    profile = profile if profile in PROFILE_RULES else "moderate"
    results: list[StockAnalysis] = []
    errors: list[str] = []
    universe = get_universe()
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(analyze_symbol, symbol, profile): symbol for symbol in universe}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                analysis = future.result()
                if analysis:
                    results.append(analysis)
            except Exception as exc:
                errors.append(f"{symbol}: {exc}")
    results.sort(key=lambda item: item.score, reverse=True)
    return results[:limit], errors


def dumps_analysis(item: StockAnalysis) -> str:
    return json.dumps(item.to_record(), ensure_ascii=True)
