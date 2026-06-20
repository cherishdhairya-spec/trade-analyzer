from __future__ import annotations

import plotly.graph_objects as go

from .data_sources import fetch_history
from .indicators import add_indicators
from .patterns import detect_patterns


def make_candlestick(symbol: str, entry: float | None = None, stoploss: float | None = None, target: float | None = None) -> str:
    df = add_indicators(fetch_history(symbol, period="1y"))
    df = df.tail(150)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name=symbol,
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA 20", line={"width": 1.3, "color": "#2563eb"}))
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA 50", line={"width": 1.3, "color": "#f59e0b"}))
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], name="SMA 200", line={"width": 1.1, "color": "#64748b"}))

    last_x = df.index[-1]
    first_x = df.index[0]
    lines = [("Entry", entry, "#0f766e"), ("Stoploss", stoploss, "#dc2626"), ("Target", target, "#16a34a")]
    for label, value, color in lines:
        if value:
            fig.add_shape(type="line", x0=first_x, x1=last_x, y0=value, y1=value, line={"color": color, "dash": "dash"})
            fig.add_annotation(x=last_x, y=value, text=f"{label}: {value:.2f}", showarrow=False, xanchor="left", font={"color": color})

    patterns = detect_patterns(df)
    for pattern in patterns:
        date = pattern["date"]
        fig.add_trace(go.Scatter(
            x=[date],
            y=[pattern["price"]],
            mode="markers+text",
            text=[pattern["name"]],
            textposition="top center",
            marker={"size": 10, "symbol": "diamond", "color": "#7c3aed"},
            name=pattern["name"],
        ))

    fig.add_trace(go.Scatter(
        x=[df.index[-1]],
        y=[df["Close"].iloc[-1]],
        mode="markers+text",
        text=[f"Close {df['Close'].iloc[-1]:.2f}"],
        textposition="bottom right",
        marker={"size": 10, "color": "#111827"},
        name="Latest close",
    ))
    fig.update_layout(
        template="plotly_white",
        margin={"l": 10, "r": 10, "t": 40, "b": 10},
        height=560,
        xaxis_rangeslider_visible=False,
        title=f"{symbol} candlestick with patterns, entry, stoploss and target",
        legend={"orientation": "h"},
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn")
