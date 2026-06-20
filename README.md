# Stock Analyzer

Local Windows dashboard for medium-term Indian stock analysis. It scans NSE stocks, ranks 30-50 candidates, selects the best 10 for a selected risk profile, draws candlestick charts with pattern markers, and can connect to Zerodha Kite Connect for holdings, margins, and optional manual order buttons.

This is not financial advice. The app estimates risk and reward from public market data and broker portfolio data. You should verify every trade yourself.

## Libraries

The app uses:

- `fastapi` and `uvicorn` for the local app
- `yfinance`, `pandas`, `numpy`, `scipy` for market data and analysis
- `plotly` for candlestick charts
- `SQLAlchemy` and SQLite for saved progress
- `APScheduler` for periodic scans while the laptop is on
- `kiteconnect` for Zerodha account, holdings, margins, and optional orders
- `playwright` for opening research pages such as Moneycontrol

## Install and Run

Open Command Prompt or PowerShell:

```powershell
cd "C:\Users\User\Documents\trading papa\stock_analyzer"
py -3 -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

You can also double-click `run_app.bat`.

## Start When Laptop Opens

Run PowerShell as your normal user:

```powershell
cd "C:\Users\User\Documents\trading papa\stock_analyzer"
powershell -ExecutionPolicy Bypass -File .\install_startup_task.ps1
```

The app scans when it starts and then keeps scanning every `SCAN_INTERVAL_HOURS` while the device is on. If the laptop is off, progress is kept in `data/stock_analyzer.db`, and the next scan runs after the app starts again.

## Zerodha Setup

You cannot connect directly to NSE/BSE as a normal retail user. You connect through a broker. With Zerodha, use Kite Connect:

1. Create an app at `https://developers.kite.trade/`.
2. Set redirect URL to `http://127.0.0.1:8000/zerodha/callback`.
3. Put `ZERODHA_API_KEY` and `ZERODHA_API_SECRET` in `.env`.
4. Restart the app.
5. Open the dashboard and use the Zerodha login button.

Official Zerodha references used:

- Kite Connect overview: https://kite.trade/docs/connect/v3/
- Python client: https://kite.trade/docs/pykiteconnect/v4/
- Portfolio APIs: https://kite.trade/docs/connect/v3/portfolio/

`ZERODHA_LIVE_TRADING=false` is the default. In that mode, Buy/Sell buttons only create paper order logs. Set it to `true` only after you understand that clicks can place real orders through Zerodha.

## Android

Keep the laptop and phone on the same Wi-Fi. Start the app on the laptop using:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Find your laptop IP with `ipconfig`, then open this on Android:

```text
http://YOUR_LAPTOP_IP:8000
```

For a true Android APK, the backend can later be reused and paired with a Flutter/React Native client.

## Put It Online

Before uploading, keep `.env`, `venv/`, and `data/` private. They are ignored by `.gitignore`.

Recommended for a beginner:

1. Create a private GitHub repository.
2. Upload the `stock_analyzer` project files, but do not upload `.env`, `venv/`, or `data/`.
3. Create a Render or Railway web service from that GitHub repository.
4. Use this build command:

```bash
pip install -r requirements.txt
```

5. Use this start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

6. Add environment variables in the host dashboard:

```text
ZERODHA_LIVE_TRADING=false
ZERODHA_API_KEY=your_key
ZERODHA_API_SECRET=your_secret
SCAN_INTERVAL_HOURS=6
RISK_PROFILE=moderate
```

7. In Zerodha Kite Connect, change the redirect URL to:

```text
https://YOUR-ONLINE-DOMAIN/zerodha/callback
```

Do not enable `ZERODHA_LIVE_TRADING=true` on a public server until the dashboard has proper login protection.
