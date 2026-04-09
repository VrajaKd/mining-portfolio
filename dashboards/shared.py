from __future__ import annotations

import pandas as pd

DISPLAY_NAMES = {
    "ticker": "Ticker",
    "score": "Score",
    "ev_adjusted": "Expected Value",
    "risk_score": "Risk",
    "action": "Action",
    "portfolio_weight_pct": "Weight %",
    "target_weight_pct": "Target %",
    "market_value": "Market Value",
    "quantity": "Quantity",
    "tier": "Tier",
    "delta_pct": "Delta %",
    "rebalance_action": "Action",
    "delta_weight_pct": "Delta %",
    "delta_value": "Delta $",
    "sell_ticker": "Sell",
    "sell_ev": "Sell EV",
    "buy_ticker": "Buy",
    "buy_ev": "Buy EV",
    "ev_improvement": "EV Improvement",
    "unrealized_pl": "Unrealized P/L",
    "commodity": "Commodity",
    "jurisdiction": "Jurisdiction",
    "company_name": "Company",
    "positions": "Positions",
    "weight": "Weight %",
    "avg_score": "Avg Score",
    "avg_ev": "Avg EV",
    "final_score": "Final Score",
}


ACTION_LABELS = {
    "NO_DATA": "No Score",
}

TIER_LABELS = {
    "core": "Core",
    "core_min": "Core (min)",
    "secondary": "Secondary",
    "speculative": "Speculative",
}


def rename_for_display(df: pd.DataFrame) -> pd.DataFrame:
    renames = {
        k: v for k, v in DISPLAY_NAMES.items() if k in df.columns
    }
    result = df.rename(columns=renames)
    action_col = DISPLAY_NAMES.get("action", "action")
    if action_col in result.columns:
        result[action_col] = result[action_col].replace(ACTION_LABELS)
    tier_col = DISPLAY_NAMES.get("tier", "tier")
    if tier_col in result.columns:
        result[tier_col] = result[tier_col].replace(TIER_LABELS)
    # Format numbers and replace NaN
    for col in result.columns:
        if result[col].dtype in ("float64", "float32"):
            result[col] = result[col].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) else "—"
            )
        else:
            result[col] = result[col].fillna("—")
    return result


ACTION_COLORS = {
    "BUY": "background-color: #6b8f71; color: white",
    "ADD": "background-color: #355070; color: white",
    "HOLD": "background-color: #eaac8b; color: #355070",
    "SELL": "background-color: #e56b6f; color: white",
    "No Score": "background-color: #f5e6d8; color: #355070",
}


def style_action_column(view: pd.DataFrame):
    """Apply action colors and return styled dataframe."""
    action_col = "Action"
    if action_col in view.columns:
        return view.style.map(
            lambda val: ACTION_COLORS.get(val, ""),
            subset=[action_col],
        )
    return view


def dataframe_height(df: pd.DataFrame, row_height: int = 35, header_height: int = 38) -> int:
    """Calculate pixel height to show all rows without a scrollbar."""
    return header_height + len(df) * row_height + 2


def get_db_path(settings: dict) -> str:
    return settings.get("paths", {}).get(
        "database", "data/processed/scoring_data.db"
    )


def load_and_enrich(
    normalized: pd.DataFrame, settings: dict
) -> pd.DataFrame:
    from modules.decision_engine import enrich_with_decisions
    from modules.ev_engine import enrich_with_ev
    from modules.persistence import init_database
    from modules.rebalance_engine import calculate_target_weights
    from modules.risk_engine import enrich_with_risk
    from modules.scoring import enrich_with_scores

    db_path = get_db_path(settings)
    init_database(db_path)

    df = enrich_with_scores(normalized, db_path)
    df = enrich_with_ev(df, db_path, settings)
    df = enrich_with_risk(df, settings)
    df = enrich_with_decisions(df, settings)
    df = calculate_target_weights(df, settings)
    return df
