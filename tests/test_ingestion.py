import pandas as pd

from modules.ingestion import normalize_holdings, validate_holdings


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
