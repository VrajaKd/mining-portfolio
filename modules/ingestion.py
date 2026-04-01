from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def connect_ib(
    host: str | None = None,
    port: int | None = None,
    client_id: int | None = None,
):
    import nest_asyncio

    # Ensure event loop exists before importing ib_insync
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    nest_asyncio.apply()

    from ib_async import IB

    host = host or os.getenv("IBKR_HOST", "localhost")
    port = port or int(os.getenv("IBKR_PORT", "7497"))
    client_id = client_id or int(os.getenv("IBKR_CLIENT_ID", "1"))
    ib = IB()
    ib.connect(host, port, clientId=client_id, timeout=20)
    return ib


def fetch_portfolio(ib) -> pd.DataFrame:
    """Read current positions from IB and return raw DataFrame."""
    positions = ib.portfolio()
    if not positions:
        return pd.DataFrame()

    rows = []
    for item in positions:
        contract = item.contract
        rows.append(
            {
                "ticker": contract.symbol,
                "company_name": contract.localSymbol or contract.symbol,
                "currency": contract.currency,
                "exchange": contract.primaryExchange or contract.exchange,
                "quantity": item.position,
                "market_value": item.marketValue,
                "avg_cost": item.averageCost,
                "unrealized_pl": item.unrealizedPNL,
            }
        )

    return pd.DataFrame(rows)


def parse_ib_csv(filepath: str | Path) -> pd.DataFrame:
    """Parse an IB CSV export as fallback when API is unavailable."""
    df = pd.read_csv(filepath)

    column_map = {
        "Symbol": "ticker",
        "Description": "company_name",
        "Currency": "currency",
        "Quantity": "quantity",
        "Market Value": "market_value",
        "Average Cost": "avg_cost",
        "Unrealized P/L": "unrealized_pl",
        "Listing Exchange": "exchange",
    }
    rename = {k: v for k, v in column_map.items() if k in df.columns}
    df = df.rename(columns=rename)

    required = ["ticker", "currency", "quantity", "market_value"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return df


def normalize_holdings(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate, aggregate, and calculate portfolio weights."""
    if raw_df.empty:
        return raw_df

    df = raw_df.copy()

    agg_rules = {
        "company_name": "first",
        "currency": "first",
        "exchange": "first",
        "quantity": "sum",
        "market_value": "sum",
        "unrealized_pl": "sum",
    }
    present_agg = {k: v for k, v in agg_rules.items() if k in df.columns}

    if "avg_cost" in df.columns:
        # Weighted average cost
        df["_cost_total"] = df["avg_cost"] * df["quantity"]
        grouped = df.groupby("ticker", as_index=False).agg(
            {**present_agg, "_cost_total": "sum"}
        )
        grouped["avg_cost"] = grouped["_cost_total"] / grouped["quantity"]
        grouped = grouped.drop(columns=["_cost_total"])
    else:
        grouped = df.groupby("ticker", as_index=False).agg(present_agg)

    total_value = grouped["market_value"].sum()
    if total_value > 0:
        grouped["portfolio_weight_pct"] = (
            grouped["market_value"] / total_value * 100
        ).round(2)
    else:
        grouped["portfolio_weight_pct"] = 0.0

    return grouped.sort_values("portfolio_weight_pct", ascending=False).reset_index(
        drop=True
    )


def validate_holdings(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    """Validate holdings. Bad rows are flagged, not dropped."""
    warnings = []

    if df.empty:
        warnings.append("Portfolio is empty")
        return df, warnings

    zero_value = df["market_value"] == 0
    if zero_value.any():
        tickers = df.loc[zero_value, "ticker"].tolist()
        warnings.append(f"Zero market value: {tickers}")

    zero_qty = df["quantity"] == 0
    if zero_qty.any():
        tickers = df.loc[zero_qty, "ticker"].tolist()
        warnings.append(f"Zero quantity: {tickers}")

    if "avg_cost" in df.columns:
        implied_price = df["market_value"] / df["quantity"].replace(0, float("nan"))
        cost_diff = ((implied_price - df["avg_cost"]).abs() / df["avg_cost"]) > 0.5
        cost_diff = cost_diff.fillna(False)
        if cost_diff.any():
            tickers = df.loc[cost_diff, "ticker"].tolist()
            warnings.append(f"Price vs avg_cost divergence >50%: {tickers}")

    return df, warnings
