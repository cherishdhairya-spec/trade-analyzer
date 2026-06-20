from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
load_dotenv(BASE_DIR / ".env")


class Settings:
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    scan_interval_hours: int = int(os.getenv("SCAN_INTERVAL_HOURS", "6"))
    default_risk_profile: str = os.getenv("RISK_PROFILE", "moderate")
    zerodha_live_trading: bool = os.getenv("ZERODHA_LIVE_TRADING", "false").lower() == "true"
    zerodha_api_key: str = os.getenv("ZERODHA_API_KEY", "")
    zerodha_api_secret: str = os.getenv("ZERODHA_API_SECRET", "")
    zerodha_user_id: str = os.getenv("ZERODHA_USER_ID", "")
    custom_universe: str = os.getenv("CUSTOM_UNIVERSE", "")
    database_url: str = f"sqlite:///{DATA_DIR / 'stock_analyzer.db'}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
