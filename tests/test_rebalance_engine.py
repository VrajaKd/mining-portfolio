import pandas as pd

from modules.rebalance_engine import (
    calculate_rebalance_plan,
    calculate_target_weights,
    check_constraints,
)

SETTINGS = {
    "model": {
        "position_size": {
            "core_min": 0.06,
            "core_max": 0.10,
            "secondary_min": 0.03,
            "secondary_max": 0.06,
            "speculative_min": 0.01,
            "speculative_max": 0.03,
        },
        "portfolio_constraints": {
            "max_single_position": 0.25,
            "max_region_exposure": 0.45,
            "max_commodity_exposure": 0.30,
        },
        "rebalance": {
            "overweight_deviation": 0.20,
            "swap_ev_multiplier": 1.25,
            "min_ev_improvement": 1.0,
        },
    }
}


def _portfolio():
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"],
            "market_value": [3000, 2500, 2000, 1500, 1000, 500],
            "portfolio_weight_pct": [28.6, 23.8, 19.0, 14.3, 9.5, 4.8],
            "tier": [
                "core", "core", "core_min",
                "secondary", "secondary", "speculative",
            ],
            "ev_adjusted": [6.0, 5.5, 4.5, 3.5, 3.2, 1.5],
        }
    )


def test_target_weights_assigned():
    df = _portfolio()
    result = calculate_target_weights(df, SETTINGS)
    assert "target_weight_pct" in result.columns
    total = result["target_weight_pct"].sum()
    assert abs(total - 100.0) < 0.5


def test_target_weights_capped():
    df = _portfolio()
    result = calculate_target_weights(df, SETTINGS)
    assert result["target_weight_pct"].max() <= 25.0


def test_rebalance_plan_columns():
    df = _portfolio()
    result = calculate_rebalance_plan(df, 10000, SETTINGS)
    assert "delta_weight_pct" in result.columns
    assert "delta_value" in result.columns
    assert "rebalance_action" in result.columns


def test_rebalance_plan_sums_near_zero():
    df = _portfolio()
    result = calculate_rebalance_plan(df, 10000, SETTINGS)
    # Delta values should roughly sum to 0 (rebalancing, not adding/removing)
    total_delta = result["delta_value"].sum()
    assert abs(total_delta) < 100.0  # Small rounding drift acceptable


def test_constraint_concentration():
    df = pd.DataFrame(
        {
            "ticker": ["BIG"],
            "portfolio_weight_pct": [30.0],
        }
    )
    violations = check_constraints(df, SETTINGS)
    assert any(v["type"] == "concentration" for v in violations)


def test_constraint_region():
    df = pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "portfolio_weight_pct": [30.0, 25.0],
            "jurisdiction": ["Australia", "Australia"],
        }
    )
    violations = check_constraints(df, SETTINGS)
    assert any(v["type"] == "region" for v in violations)


def test_constraint_commodity():
    df = pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "portfolio_weight_pct": [20.0, 15.0],
            "commodity": ["Gold", "Gold"],
        }
    )
    violations = check_constraints(df, SETTINGS)
    assert any(v["type"] == "commodity" for v in violations)


def test_no_violations():
    df = pd.DataFrame(
        {
            "ticker": ["A", "B", "C"],
            "portfolio_weight_pct": [10.0, 10.0, 10.0],
            "jurisdiction": ["Australia", "Canada", "USA"],
            "commodity": ["Gold", "Copper", "Uranium"],
        }
    )
    violations = check_constraints(df, SETTINGS)
    assert violations == []
