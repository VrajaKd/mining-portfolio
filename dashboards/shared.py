from __future__ import annotations

import pandas as pd


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
