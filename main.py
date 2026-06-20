from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from charts import make_candlestick
from config import BASE_DIR, get_settings
from database import ScanRun, StockScore, db_session, init_db
from scoring import dumps_analysis, run_scan
from zerodha import create_session, holdings, login_url, margins, order_logs, place_order

app = FastAPI(title="Stock Analyzer")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
scheduler = BackgroundScheduler()


def save_scan(profile: str) -> dict[str, Any]:
    candidates, errors = run_scan(profile=profile, limit=50)
    with db_session() as session:
        scan = ScanRun(risk_profile=profile, universe_size=len(candidates), notes="\n".join(errors[:30]))
        session.add(scan)
        session.flush()
        for rank, item in enumerate(candidates, start=1):
            record = item.to_record()
            session.add(StockScore(
                run_id=scan.id,
                symbol=item.symbol,
                name=item.name,
                sector=item.sector,
                score=item.score,
                rank=rank,
                action=item.action,
                risk_category=item.risk_category,
                entry=item.entry,
                stoploss=item.stoploss,
                target=item.target,
                reward_pct=item.reward_pct,
                risk_pct=item.risk_pct,
                pe_ratio=item.pe_ratio,
                market_cap=item.market_cap,
                turnover=item.turnover,
                volatility=item.volatility,
                std_dev=item.std_dev,
                alpha=item.alpha,
                beta=item.beta,
                rsi=item.rsi,
                patterns=json.dumps(item.patterns, ensure_ascii=True),
                summary=f"{item.current_situation}\n{item.risks}\n{item.profit_case}",
                raw_json=dumps_analysis(item),
            ))
        return {"run_id": scan.id, "count": len(candidates), "errors": errors[:20]}


def latest_scan(profile: str) -> dict[str, Any]:
    with db_session() as session:
        scan = session.query(ScanRun).filter(ScanRun.risk_profile == profile).order_by(ScanRun.created_at.desc()).first()
        if not scan:
            return {"scan": None, "top10": [], "candidates": []}
        rows = session.query(StockScore).filter(StockScore.run_id == scan.id).order_by(StockScore.rank.asc()).all()
        payload = [json.loads(row.raw_json) for row in rows]
        return {
            "scan": {
                "id": scan.id,
                "created_at": scan.created_at.isoformat(),
                "risk_profile": scan.risk_profile,
                "notes": scan.notes,
            },
            "top10": payload[:10],
            "candidates": payload,
        }


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    settings = get_settings()
    if not scheduler.running:
        scheduler.add_job(lambda: save_scan(settings.default_risk_profile), "interval", hours=settings.scan_interval_hours, id="scan", replace_existing=True)
        scheduler.start()
    # Run one startup scan only when there is no saved scan yet.
    if latest_scan(settings.default_risk_profile)["scan"] is None:
        scheduler.add_job(lambda: save_scan(settings.default_risk_profile), id="initial_scan", replace_existing=True)


@app.on_event("shutdown")
def on_shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"live_trading": get_settings().zerodha_live_trading})


@app.post("/api/scan")
def api_scan(profile: str = Form("moderate")) -> dict[str, Any]:
    profile = profile if profile in {"less", "moderate", "high"} else "moderate"
    result = save_scan(profile)
    result["latest"] = latest_scan(profile)
    return result


@app.get("/api/latest")
def api_latest(profile: str = "moderate") -> dict[str, Any]:
    profile = profile if profile in {"less", "moderate", "high"} else "moderate"
    return latest_scan(profile)


@app.get("/api/chart/{symbol}", response_class=HTMLResponse)
def api_chart(symbol: str, entry: float | None = None, stoploss: float | None = None, target: float | None = None) -> HTMLResponse:
    return HTMLResponse(make_candlestick(symbol, entry=entry, stoploss=stoploss, target=target))


@app.get("/api/zerodha")
def api_zerodha() -> dict[str, Any]:
    return {
        "login_url": login_url(),
        "margins": margins(),
        "holdings": holdings(),
        "live_trading": get_settings().zerodha_live_trading,
        "orders": order_logs(),
    }


@app.get("/zerodha/callback")
def zerodha_callback(request_token: str | None = None, status: str | None = None) -> RedirectResponse:
    if status == "success" and request_token:
        create_session(request_token)
    return RedirectResponse("/")


@app.post("/api/order")
def api_order(symbol: str = Form(...), side: str = Form(...), quantity: int = Form(...)) -> JSONResponse:
    try:
        return JSONResponse(place_order(symbol=symbol, side=side, quantity=quantity))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/open-research/{symbol}")
def open_research(symbol: str) -> dict[str, str]:
    # Kept as URLs so the user can open sources in their own browser.
    clean = symbol.upper().replace(".NS", "")
    return {
        "moneycontrol": f"https://www.moneycontrol.com/india/stockpricequote/{clean}",
        "screener": f"https://www.screener.in/company/{clean}/",
        "nse": f"https://www.nseindia.com/get-quotes/equity?symbol={clean}",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "project": str(BASE_DIR)}
