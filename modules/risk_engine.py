from __future__ import annotations

import pandas as pd


def calculate_risk(
    score: float | None,
    ev: float | None,
    manual_override: int | None = None,
    settings: dict | None = None,
) -> int:
    """Watchlist risk score 5-10. Lower is better."""
    if manual_override is not None:
        return max(5, min(10, manual_override))

    if score is None and ev is None:
        return 7  # Unknown = moderate risk

    # Thresholds from config or defaults
    thresholds = {}
    if settings:
        thresholds = (
            settings.get("model", {}).get("risk_thresholds", {})
        )
    score_sell = thresholds.get("score_sell", 6.5)
    score_weak = thresholds.get("score_weak", 7.0)
    score_ok = thresholds.get("score_ok", 7.5)
    score_good = thresholds.get("score_good", 8.0)
    ev_sell = thresholds.get("ev_sell", 2.5)
    ev_weak = thresholds.get("ev_weak", 3.0)
    ev_ok = thresholds.get("ev_ok", 3.5)
    ev_good = thresholds.get("ev_good", 4.5)

    s = score if score is not None else 7.0
    e = ev if ev is not None else 3.5

    if s < score_sell or e < ev_sell:
        return 9
    elif s < score_weak or e < ev_weak:
        return 8
    elif s < score_ok or e < ev_ok:
        return 7
    elif s >= score_good and e >= ev_good:
        return 5
    return 6


def get_risk_flags(risk: int, settings: dict) -> list[str]:
    thresholds = settings.get("model", {}).get("risk_thresholds", {})
    sell_threshold = thresholds.get("sell_candidate", 9)
    weak_threshold = thresholds.get("weak_holding", 7)

    flags = []
    if risk >= sell_threshold:
        flags.extend(["SELL_CANDIDATE", "SWAP_ELIGIBLE"])
    elif risk >= weak_threshold:
        flags.append("WEAK_HOLDING")
    return flags


def enrich_with_risk(
    df: pd.DataFrame, settings: dict
) -> pd.DataFrame:
    """Add risk_score and risk_flags columns."""
    result = df.copy()
    result["risk_score"] = result.apply(
        lambda row: calculate_risk(
            row.get("score"), row.get("ev_adjusted"), settings=settings
        ),
        axis=1,
    )
    result["risk_flags"] = result["risk_score"].apply(
        lambda r: get_risk_flags(r, settings)
    )
    return result
