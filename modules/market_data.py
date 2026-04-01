from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

EXCHANGE_SUFFIX = {
    "ASX": ".AX",
    "TSX": ".TO",
    "TSXV": ".V",
    "VENTURE": ".V",
    "NYSE": "",
    "NASDAQ": "",
    "ARCA": "",
    "IBIS": ".DE",
    "XETRA": ".DE",
    "LSE": ".L",
    "": "",
}


def map_ticker_to_yfinance(ticker: str, exchange: str) -> str:
    """Map a broker ticker + exchange to a yfinance-compatible symbol."""
    exchange_upper = (exchange or "").upper()
    suffix = EXCHANGE_SUFFIX.get(exchange_upper, "")
    return f"{ticker}{suffix}"


def fetch_market_data(tickers: list[str]) -> pd.DataFrame:
    """Fetch EOD market data for a list of yfinance-compatible tickers."""
    if not tickers:
        return pd.DataFrame()

    rows = []
    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            if hist.empty:
                logger.warning("No history for %s", ticker)
                rows.append(_empty_row(ticker))
                continue

            last = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else last

            prev_close = float(prev["Close"])
            current_price = float(last["Close"])
            day_change_pct = (
                ((current_price - prev_close) / prev_close * 100)
                if prev_close > 0
                else 0.0
            )

            rows.append(
                {
                    "yf_ticker": ticker,
                    "current_price": round(current_price, 4),
                    "day_change_pct": round(day_change_pct, 2),
                    "volume": int(last["Volume"]),
                }
            )
        except Exception:
            logger.warning("No data for %s", ticker)
            rows.append(_empty_row(ticker))

    return pd.DataFrame(rows)


def _empty_row(ticker: str) -> dict:
    return {
        "yf_ticker": ticker,
        "current_price": None,
        "day_change_pct": None,
        "volume": None,
    }


def fetch_market_caps(tickers: list[str]) -> dict[str, float | None]:
    """Fetch market cap for each ticker via yfinance info."""
    caps = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            caps[ticker] = info.get("marketCap")
        except Exception:
            logger.warning("Failed to get market cap for %s", ticker)
            caps[ticker] = None
    return caps


def enrich_holdings(df: pd.DataFrame) -> pd.DataFrame:
    """Add market data columns to a normalized holdings DataFrame."""
    if df.empty:
        return df

    result = df.copy()

    exchange_col = "exchange" if "exchange" in result.columns else None
    yf_tickers = []
    for _, row in result.iterrows():
        exchange = row[exchange_col] if exchange_col else ""
        yf_tickers.append(map_ticker_to_yfinance(row["ticker"], exchange or ""))

    result["yf_ticker"] = yf_tickers

    price_df = fetch_market_data(yf_tickers)
    if not price_df.empty:
        result = result.merge(price_df, on="yf_ticker", how="left")

    caps = fetch_market_caps(yf_tickers)
    result["market_cap"] = result["yf_ticker"].map(caps)

    result["price_timestamp"] = datetime.now(timezone.utc).isoformat()

    warnings = []
    missing = result["current_price"].isna()
    if missing.any():
        tickers = result.loc[missing, "ticker"].tolist()
        warnings.append(f"No market data for: {tickers}")
        for w in warnings:
            logger.warning(w)

    return result
