import pandas as pd
import pytest

from modules.ingestion import normalize_holdings, validate_holdings, parse_ib_csv


def _sample_df(**overrides):
    base = {
        "ticker": ["AAA", "BBB"],
        "company_name": ["Alpha Mining", "Beta Resources"],
        "currency": ["AUD", "CAD"],
        "exchange": ["ASX", "TSX"],
        "quantity": [1000, 2000],
        "market_value": [5000.0, 10000.0],
        "avg_cost": [4.5, 5.0],
        "unrealized_pl": [500.0, 0.0],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_normalize_deduplicates():
    df = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB"],
            "company_name": ["Alpha", "Alpha", "Beta"],
            "currency": ["AUD", "AUD", "CAD"],
            "exchange": ["ASX", "ASX", "TSX"],
            "quantity": [500, 500, 2000],
            "market_value": [2500.0, 2500.0, 10000.0],
            "avg_cost": [4.0, 5.0, 5.0],
            "unrealized_pl": [250.0, 250.0, 0.0],
        }
    )
    result = normalize_holdings(df)
    assert len(result) == 2
    aaa = result[result["ticker"] == "AAA"].iloc[0]
    assert aaa["quantity"] == 1000
    assert aaa["market_value"] == 5000.0


def test_normalize_calculates_weights():
    df = _sample_df()
    result = normalize_holdings(df)
    total_weight = result["portfolio_weight_pct"].sum()
    assert abs(total_weight - 100.0) < 0.1


def test_normalize_empty():
    result = normalize_holdings(pd.DataFrame())
    assert result.empty


def test_validate_flags_zero_value():
    df = _sample_df(market_value=[0.0, 10000.0])
    df = normalize_holdings(df)
    _, warnings = validate_holdings(df)
    assert any("Zero market value" in w for w in warnings)


def test_validate_flags_zero_quantity():
    df = _sample_df(quantity=[0, 2000])
    df = normalize_holdings(df)
    _, warnings = validate_holdings(df)
    assert any("Zero quantity" in w for w in warnings)


def test_validate_empty():
    _, warnings = validate_holdings(pd.DataFrame())
    assert any("empty" in w.lower() for w in warnings)


def test_validate_price_divergence():
    df = _sample_df(
        market_value=[10000.0, 10000.0],
        quantity=[1000, 2000],
        avg_cost=[1.0, 5.0],
    )
    df = normalize_holdings(df)
    _, warnings = validate_holdings(df)
    assert any("divergence" in w.lower() for w in warnings)


# --- CSV parsing tests ---


def test_parse_activity_statement():
    df = parse_ib_csv("data/sample_activity_statement.csv")
    assert not df.empty
    assert "ticker" in df.columns
    assert "market_value" in df.columns
    assert df.attrs.get("account_summary")


def test_parse_tws_export():
    df = parse_ib_csv("data/sample_tws_export.csv")
    assert not df.empty
    assert "ticker" in df.columns


def test_parse_mtm_summary():
    df = parse_ib_csv("data/U8325074_20260408 9-4-2026.csv")
    assert len(df) == 16
    assert "ticker" in df.columns
    assert "company_name" in df.columns
    assert "market_value" in df.columns
    assert "quantity" in df.columns
    # Check known positions
    tickers = set(df["ticker"])
    assert "SGQ" in tickers
    assert "BIG" in tickers
    # Account summary should be populated
    summary = df.attrs.get("account_summary", {})
    assert summary.get("net_liquidation") > 0
    assert summary.get("cash") is not None


def test_parse_mtm_filters_stocks_only():
    df = parse_ib_csv("data/U8325074_20260408 9-4-2026.csv")
    # Should only contain stock positions, not forex
    currencies = set(df["currency"])
    assert currencies <= {"AUD", "CAD"}


def test_parse_invalid_csv(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("Statement,Data,foo,bar\n")
    with pytest.raises(ValueError):
        parse_ib_csv(str(bad))
