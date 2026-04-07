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

    # Ensure event loop exists before importing ib_async
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

    df = pd.DataFrame(rows)

    # Account summary
    summary = {}
    try:
        account_values = ib.accountSummary()
        for av in account_values:
            if av.tag == "NetLiquidation":
                summary["net_liquidation"] = float(av.value)
            elif av.tag == "TotalCashValue":
                summary["cash"] = float(av.value)
            elif av.tag == "GrossPositionValue":
                summary["gross_exposure"] = float(av.value)
    except Exception:
        pass
    df.attrs["account_summary"] = summary

    return df


def _parse_activity_statement(filepath: str | Path) -> pd.DataFrame:
    """Parse IB Activity Statement CSV (multi-section format)."""
    # Detect max columns, then read with enough space
    import csv
    import io

    if hasattr(filepath, "read"):
        content = filepath.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")
    else:
        content = Path(filepath).read_text(encoding="utf-8-sig")
    content = content.lstrip("\ufeff")
    reader = csv.reader(io.StringIO(content))
    max_cols = max(len(row) for row in reader)
    col_names = list(range(max_cols))
    raw = pd.read_csv(
        io.StringIO(content), header=None, names=col_names,
        dtype=str, keep_default_na=False,
    )

    # Find Open Positions data rows
    mask = (raw.iloc[:, 0] == "Open Positions") & (raw.iloc[:, 1] == "Data")
    positions = raw[mask].copy()
    if positions.empty:
        raise ValueError("No Open Positions found in Activity Statement")

    # Filter Summary rows only (skip Total rows)
    positions = positions[positions.iloc[:, 2] == "Summary"]
    if positions.empty:
        raise ValueError("No Open Positions Summary rows found")

    # Header is at row where col[1] == "Header"
    header_mask = (raw.iloc[:, 0] == "Open Positions") & (raw.iloc[:, 1] == "Header")
    header_row = raw[header_mask].iloc[0].tolist()

    # Build DataFrame with proper column names
    positions.columns = header_row
    positions = positions.rename(columns={
        "Symbol": "ticker",
        "Currency": "currency",
        "Quantity": "quantity",
        "Cost Price": "avg_cost",
        "Value": "market_value",
        "Unrealized P/L": "unrealized_pl",
    })

    # Get description from Financial Instrument Information section
    fi_section = "Financial Instrument Information"
    fi_mask = (raw.iloc[:, 0] == fi_section) & (raw.iloc[:, 1] == "Data")
    fi_rows = raw[fi_mask]
    if not fi_rows.empty:
        fi_header_mask = (
            (raw.iloc[:, 0] == fi_section) & (raw.iloc[:, 1] == "Header")
        )
        fi_header = raw[fi_header_mask].iloc[0].tolist()
        fi_df = fi_rows.copy()
        fi_df.columns = fi_header
        desc_map = dict(zip(fi_df["Symbol"], fi_df["Description"]))
        positions["company_name"] = positions["ticker"].map(desc_map)

    # Convert numeric columns
    for col in ["quantity", "avg_cost", "market_value", "unrealized_pl"]:
        if col in positions.columns:
            positions[col] = pd.to_numeric(positions[col], errors="coerce")

    required = ["ticker", "currency", "quantity", "market_value"]
    missing = [c for c in required if c not in positions.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Extract account summary from NAV section
    nav_mask = (
        (raw.iloc[:, 0] == "Net Asset Value")
        & (raw.iloc[:, 1] == "Data")
    )
    nav_rows = raw[nav_mask]
    account_summary = {}
    # NAV columns: 2=label, 3=Prior, 4=Long, 5=Short, 6=Total, 7=Change
    for _, row in nav_rows.iterrows():
        label = str(row.iloc[2]).strip()
        if label == "Total":
            account_summary["net_liquidation"] = _to_float(
                row.iloc[6]
            )
        elif label.startswith("Cash"):
            account_summary["cash"] = _to_float(row.iloc[6])
        elif label == "Stock":
            account_summary["stock_value"] = _to_float(
                row.iloc[6]
            )

    result = positions[
        [c for c in [
            "ticker", "company_name", "currency", "quantity",
            "market_value", "avg_cost", "unrealized_pl",
        ] if c in positions.columns]
    ].reset_index(drop=True)
    result.attrs["account_summary"] = account_summary
    return result


def _to_float(val) -> float | None:
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None


def _parse_simple_csv(filepath: str | Path) -> pd.DataFrame:
    """Parse simple CSV with standard column headers."""
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


def parse_ib_csv(filepath: str | Path) -> pd.DataFrame:
    """Parse IB CSV — auto-detects Activity Statement or simple format."""
    import csv
    import io

    if hasattr(filepath, "read"):
        content = filepath.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        filepath.seek(0)
    else:
        content = Path(filepath).read_text()

    reader = csv.reader(io.StringIO(content))
    first_row = next(reader, [])
    first_cell = first_row[0].strip().lstrip("\ufeff") if first_row else ""

    if first_cell == "Statement":
        return _parse_activity_statement(filepath)
    return _parse_simple_csv(filepath)


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
