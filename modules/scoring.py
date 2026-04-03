from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from modules.persistence import SCORE_CRITERIA, load_all_scores


def calculate_weighted_score(
    raw_scores: dict[str, float], weights: dict[str, float]
) -> float:
    """Weighted average of criterion scores. Weights sum to 1.0."""
    total = 0.0
    for criterion in SCORE_CRITERIA:
        score = raw_scores.get(criterion)
        weight = weights.get(criterion, 0.0)
        if score is not None:
            total += score * weight
    return round(total, 2)


def validate_scores(
    raw_scores: dict[str, float],
) -> tuple[bool, list[str]]:
    warnings = []
    for criterion in SCORE_CRITERIA:
        val = raw_scores.get(criterion)
        if val is None:
            warnings.append(f"Missing score: {criterion}")
        elif not 0 <= val <= 10:
            warnings.append(f"{criterion} out of range: {val}")
    return len(warnings) == 0, warnings


def validate_weights(weights: dict[str, float]) -> tuple[bool, list[str]]:
    warnings = []
    total = sum(weights.get(c, 0.0) for c in SCORE_CRITERIA)
    if abs(total - 1.0) > 0.01:
        warnings.append(f"Weights sum to {total:.3f}, expected 1.0")
    for c in SCORE_CRITERIA:
        if c not in weights:
            warnings.append(f"Missing weight for: {c}")
    return len(warnings) == 0, warnings


def load_rubrics(rubrics_path: str | Path) -> dict:
    with open(rubrics_path) as f:
        return yaml.safe_load(f)


def get_scoring_rubric(
    rubrics: dict, criterion: str, score: float
) -> str:
    crit = rubrics.get(criterion, {})
    bands = crit.get("bands", {})
    if score >= 9:
        return bands.get("9-10", "")
    elif score >= 7:
        return bands.get("7-8", "")
    elif score >= 5:
        return bands.get("5-6", "")
    elif score >= 3:
        return bands.get("3-4", "")
    return bands.get("0-2", "")


def enrich_with_scores(
    df: pd.DataFrame, db_path: str | Path
) -> pd.DataFrame:
    """Add final_score column from database."""
    result = df.copy()
    scores_df = load_all_scores(db_path)

    if scores_df.empty:
        result["score"] = None
        return result

    score_map = scores_df.set_index("ticker")["final_score"].to_dict()
    result["score"] = result["ticker"].map(score_map)
    return result
