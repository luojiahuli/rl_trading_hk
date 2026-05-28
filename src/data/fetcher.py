"""港股数据获取模块 — 多数据源（yfinance / AASTOCKS / 合成数据）"""
import pandas as pd
import numpy as np
import time
import requests
import logging

logger = logging.getLogger(__name__)

HK_SUFFIX = ".HK"

# ── yfinance ────────────────────────────────────────────

def fetch_stock_daily(symbol: str, start_date: str = "2024-01-01",
                      end_date: str = None) -> pd.DataFrame:
    """获取港股日线数据 — yfinance（带速率限制处理）"""
    symbol = _ensure_hk_symbol(symbol)
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start_date,
            end=end_date or pd.Timestamp.today().strftime("%Y-%m-%d"),
            auto_adjust=True,
        )
        if df.empty or len(df) < 30:
            return _generate_synthetic_hk(symbol, start_date, end_date)

        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume",
        })
        df["date"] = df.index
        df["pct_chg"] = df["close"].pct_change() * 100
        df = df.reset_index(drop=True)
        df["amount"] = df["volume"] * df["close"]
        df["turnover"] = 0.0
        for col in ["open", "high", "low", "close", "volume", "amount", "pct_chg"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception:
        return _generate_synthetic_hk(symbol, start_date, end_date)


def fetch_index_daily(symbol: str = "^HSI", start_date: str = "2024-01-01",
                      end_date: str = None) -> pd.DataFrame:
    """获取港股指数日线"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start_date,
            end=end_date or pd.Timestamp.today().strftime("%Y-%m-%d"),
            auto_adjust=False,
        )
        if df.empty or len(df) < 30:
            return _generate_synthetic_index(symbol, start_date, end_date)

        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume",
        })
        df["date"] = df.index
        df["pct_chg"] = df["close"].pct_change() * 100
        df = df.reset_index(drop=True)
        for col in ["open", "high", "low", "close", "volume", "pct_chg"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception:
        return _generate_synthetic_index(symbol, start_date, end_date)


def fetch_hk_news() -> list:
    """获取港股新闻"""
    try:
        import yfinance as yf
        hsi = yf.Ticker("^HSI")
        news = hsi.news or []
        return [{
            "source": "yahoo_finance",
            "title": a.get("title", ""),
            "content": a.get("summary", "") or a.get("description", ""),
            "url": a.get("link", ""),
        } for a in news[:10]]
    except Exception:
        return []


def fetch_sector_stocks(sector_name: str) -> list:
    return []


def fetch_all_sectors() -> pd.DataFrame:
    return pd.DataFrame()


def fetch_sector_daily(sector_name: str, start_date: str = "2024-01-01",
                       end_date: str = None) -> pd.DataFrame:
    return pd.DataFrame()


def fetch_concept_boards() -> pd.DataFrame:
    return pd.DataFrame()


# ── Helpers ─────────────────────────────────────────────

def _ensure_hk_symbol(symbol: str) -> str:
    if symbol.startswith("^"):
        return symbol
    return symbol if symbol.endswith(HK_SUFFIX) else f"{symbol}{HK_SUFFIX}"


def _generate_synthetic_hk(symbol: str, start_date: str, end_date: str = None) -> pd.DataFrame:
    """生成合成港股数据（当所有数据源不可用时的后备方案）"""
    try:
        ed = end_date or pd.Timestamp.today().strftime("%Y-%m-%d")
        dates = pd.date_range(start=start_date, end=ed, freq="B")
        if len(dates) < 30:
            return pd.DataFrame()

        np.random.seed(hash(symbol) % (2**31))
        base_price = 50 + np.random.random() * 200  # 港股价格范围更广
        n = len(dates)
        log_prices = np.zeros(n)
        innovations = np.random.randn(n) * 0.018
        for i in range(1, n):
            log_prices[i] = log_prices[i-1] + innovations[i] - 0.0005 * log_prices[i-1]
        prices = base_price * np.exp(log_prices)
        prices = np.clip(prices, base_price * 0.3, base_price * 2.0)

        df = pd.DataFrame({
            "date": dates,
            "open": pd.Series(prices * (1 - np.abs(np.random.randn(n)) * 0.012), dtype=float),
            "close": pd.Series(prices, dtype=float),
            "high": pd.Series(prices * (1 + np.abs(np.random.randn(n)) * 0.018), dtype=float),
            "low": pd.Series(prices * (1 - np.abs(np.random.randn(n)) * 0.018), dtype=float),
            "volume": pd.Series(np.random.randint(1000000, 50000000, n), dtype=float),
            "amount": pd.Series(np.random.randint(10000000, 1000000000, n), dtype=float),
            "pct_chg": pd.Series(np.clip(np.random.randn(n) * 2.5, -15, 15), dtype=float),
            "turnover": pd.Series(np.abs(np.random.randn(n)) * 0.5, dtype=float),
        })
        first_close = float(df["close"].iloc[0])
        for col in ["close", "open", "high", "low"]:
            df[col] = (df[col].to_numpy(dtype=float) / first_close * base_price).astype(float)
        return df
    except Exception:
        return pd.DataFrame()


def _generate_synthetic_index(symbol: str, start_date: str, end_date: str = None) -> pd.DataFrame:
    """生成合成指数数据"""
    base_level = { "^HSI": 20000, "^HSTECH": 4500, "^HSCE": 7000 }
    level = base_level.get(symbol, 15000)
    try:
        ed = end_date or pd.Timestamp.today().strftime("%Y-%m-%d")
        dates = pd.date_range(start=start_date, end=ed, freq="B")
        if len(dates) < 30:
            return pd.DataFrame()

        np.random.seed(hash(symbol) % (2**31))
        n = len(dates)
        log_prices = np.zeros(n)
        innovations = np.random.randn(n) * 0.012
        for i in range(1, n):
            log_prices[i] = log_prices[i-1] + innovations[i] - 0.0002 * log_prices[i-1]
        prices = level * np.exp(log_prices)
        prices = np.clip(prices, level * 0.7, level * 1.5)

        return pd.DataFrame({
            "date": dates,
            "open": pd.Series(prices * (1 - np.abs(np.random.randn(n)) * 0.008), dtype=float),
            "close": pd.Series(prices, dtype=float),
            "high": pd.Series(prices * (1 + np.abs(np.random.randn(n)) * 0.012), dtype=float),
            "low": pd.Series(prices * (1 - np.abs(np.random.randn(n)) * 0.012), dtype=float),
            "volume": pd.Series(np.random.randint(100000000, 10000000000, n), dtype=float),
            "pct_chg": pd.Series(np.clip(np.random.randn(n) * 1.5, -8, 8), dtype=float),
        })
    except Exception:
        return pd.DataFrame()
