from __future__ import annotations

from datetime import datetime
from typing import Any

from kiteconnect import KiteConnect

from .config import get_settings
from .database import OrderLog, Setting, db_session


def _kite() -> KiteConnect | None:
    settings = get_settings()
    if not settings.zerodha_api_key:
        return None
    kite = KiteConnect(api_key=settings.zerodha_api_key)
    token = get_setting("zerodha_access_token")
    if token:
        kite.set_access_token(token)
    return kite


def get_setting(key: str) -> str:
    with db_session() as session:
        setting = session.get(Setting, key)
        return setting.value if setting else ""


def set_setting(key: str, value: str) -> None:
    with db_session() as session:
        setting = session.get(Setting, key)
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            session.add(Setting(key=key, value=value))


def login_url() -> str:
    kite = _kite()
    if not kite:
        return ""
    return kite.login_url()


def create_session(request_token: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.zerodha_api_key or not settings.zerodha_api_secret:
        raise RuntimeError("ZERODHA_API_KEY and ZERODHA_API_SECRET are required.")
    kite = KiteConnect(api_key=settings.zerodha_api_key)
    data = kite.generate_session(request_token, api_secret=settings.zerodha_api_secret)
    set_setting("zerodha_access_token", data["access_token"])
    return data


def margins() -> dict[str, Any]:
    kite = _kite()
    if not kite:
        return {"enabled": False, "message": "Zerodha API key not configured."}
    try:
        return {"enabled": True, "data": kite.margins()}
    except Exception as exc:
        return {"enabled": True, "error": str(exc)}


def holdings() -> dict[str, Any]:
    kite = _kite()
    if not kite:
        return {"enabled": False, "holdings": [], "message": "Zerodha API key not configured."}
    try:
        return {"enabled": True, "holdings": kite.holdings()}
    except Exception as exc:
        return {"enabled": True, "holdings": [], "error": str(exc)}


def place_order(symbol: str, side: str, quantity: int, order_type: str = "MARKET", price: float | None = None) -> dict[str, Any]:
    side = side.upper()
    mode = "live" if get_settings().zerodha_live_trading else "paper"
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    if side not in {"BUY", "SELL"}:
        raise ValueError("Side must be BUY or SELL.")

    if mode == "paper":
        message = f"Paper {side} logged for {quantity} x {symbol}."
        with db_session() as session:
            session.add(OrderLog(symbol=symbol, side=side, quantity=quantity, mode=mode, status="paper", message=message))
        return {"mode": mode, "status": "paper", "message": message}

    kite = _kite()
    if not kite:
        raise RuntimeError("Zerodha is not configured.")
    order_kwargs: dict[str, Any] = {
        "variety": kite.VARIETY_REGULAR,
        "exchange": kite.EXCHANGE_NSE,
        "tradingsymbol": symbol.upper().replace(".NS", ""),
        "transaction_type": kite.TRANSACTION_TYPE_BUY if side == "BUY" else kite.TRANSACTION_TYPE_SELL,
        "quantity": quantity,
        "product": kite.PRODUCT_CNC,
        "order_type": order_type,
    }
    if price and order_type != "MARKET":
        order_kwargs["price"] = price
    order_id = kite.place_order(**order_kwargs)
    with db_session() as session:
        session.add(OrderLog(symbol=symbol, side=side, quantity=quantity, mode=mode, status="sent", broker_order_id=str(order_id)))
    return {"mode": mode, "status": "sent", "order_id": order_id}


def order_logs(limit: int = 25) -> list[dict[str, Any]]:
    with db_session() as session:
        logs = session.query(OrderLog).order_by(OrderLog.created_at.desc()).limit(limit).all()
        return [
            {
                "created_at": log.created_at.isoformat(),
                "symbol": log.symbol,
                "side": log.side,
                "quantity": log.quantity,
                "mode": log.mode,
                "status": log.status,
                "message": log.message,
                "broker_order_id": log.broker_order_id,
            }
            for log in logs
        ]
