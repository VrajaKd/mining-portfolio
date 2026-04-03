from __future__ import annotations

import pandas as pd


def determine_action(
    score: float | None,
    ev: float | None,
    risk: int | None,
    settings: dict,
) -> str:
    """Determine action: BUY, ADD, HOLD, SELL, or NO_DATA."""
    decision = settings.get("model", {}).get("decision", {})
    sell_risk = decision.get("sell_risk_min", 9)
    buy_score = decision.get("buy_score_min", 8.4)
    buy_ev = decision.get("buy_ev_min", 4.5)
    add_ev = decision.get("add_ev_min", 5.0)
    hold_score = decision.get("hold_score_min", 7.0)

    if score is None and ev is None:
        return "NO_DATA"

    # Priority: SELL > BUY > ADD > HOLD
    if risk is not None and risk >= sell_risk:
        return "SELL"

    s = score if score is not None else 0.0
    e = ev if ev is not None else 0.0

    if s >= buy_score and e >= buy_ev:
        return "BUY"
    if s >= hold_score and e >= add_ev:
        return "ADD"
    if s >= hold_score:
        return "HOLD"
    return "SELL"


def find_swap_candidates(
    df: pd.DataFrame, settings: dict
) -> pd.DataFrame:
    """Find swap pairs: sell weak holdings, replace with stronger ones."""
    rebalance = settings.get("model", {}).get("rebalance", {})
    swap_multiplier = rebalance.get("swap_ev_multiplier", 1.25)
    min_improvement = rebalance.get("min_ev_improvement", 1.0)
    sell_threshold = (
        settings.get("model", {}).get("risk_thresholds", {}).get("sell_candidate", 9)
    )

    sell_candidates = df[df["risk_score"] >= sell_threshold].copy()
    buy_pool = df[
        (df["action"].isin(["BUY", "ADD"])) & (df["risk_score"] < sell_threshold)
    ].copy()

    if sell_candidates.empty or buy_pool.empty:
        return pd.DataFrame(
            columns=[
                "sell_ticker",
                "sell_ev",
                "buy_ticker",
                "buy_ev",
                "ev_improvement",
            ]
        )

    swaps = []
    for _, sell_row in sell_candidates.iterrows():
        sell_ev = sell_row.get("ev_adjusted") or 0
        for _, buy_row in buy_pool.iterrows():
            buy_ev = buy_row.get("ev_adjusted") or 0
            improvement = buy_ev - sell_ev
            if buy_ev >= sell_ev * swap_multiplier and improvement >= min_improvement:
                swaps.append(
                    {
                        "sell_ticker": sell_row["ticker"],
                        "sell_ev": sell_ev,
                        "buy_ticker": buy_row["ticker"],
                        "buy_ev": buy_ev,
                        "ev_improvement": round(improvement, 2),
                    }
                )

    result = pd.DataFrame(swaps)
    if not result.empty:
        result = result.sort_values("ev_improvement", ascending=False)
    return result


def enrich_with_decisions(
    df: pd.DataFrame, settings: dict
) -> pd.DataFrame:
    """Add action column."""
    result = df.copy()
    result["action"] = result.apply(
        lambda row: determine_action(
            row.get("score"),
            row.get("ev_adjusted"),
            row.get("risk_score"),
            settings,
        ),
        axis=1,
    )
    return result
