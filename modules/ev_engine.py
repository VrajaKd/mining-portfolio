from __future__ import annotations

from pathlib import Path

import pandas as pd

from modules.persistence import load_all_ev_data

CATALYST_MULTIPLIERS = {
    "near_term": 1.2,
    "mid_term": 1.0,
    "long_term": 0.8,
}


def calculate_ev(
    upside_multiple: float,
    success_probability: float,
    downside: float,
    catalyst_timing: str,
    settings: dict | None = None,
) -> dict:
    """EV = (upside × probability) - downside, adjusted by catalyst timing."""
    multipliers = CATALYST_MULTIPLIERS
    if settings:
        multipliers = (
            settings.get("model", {})
            .get("ev_model", {})
            .get("catalyst_multipliers", multipliers)
        )

    catalyst_multiplier = multipliers.get(catalyst_timing, 1.0)
    ev_raw = (upside_multiple * success_probability) - downside
    ev_adjusted = round(ev_raw * catalyst_multiplier, 2)

    return {
        "upside_multiple": upside_multiple,
        "success_probability": success_probability,
        "downside": downside,
        "catalyst_timing": catalyst_timing,
        "catalyst_multiplier": catalyst_multiplier,
        "ev_raw": round(ev_raw, 2),
        "ev_adjusted": ev_adjusted,
    }


def validate_ev_inputs(
    upside_multiple: float,
    success_probability: float,
    downside: float,
    settings: dict | None = None,
) -> tuple[bool, list[str]]:
    warnings = []
    prob_min = 0.25
    prob_max = 0.80
    up_min = 5
    up_max = 50

    if settings:
        ev_model = settings.get("model", {}).get("ev_model", {})
        prob_range = ev_model.get("probability_range", {})
        up_range = ev_model.get("upside_range", {})
        prob_min = prob_range.get("min", prob_min)
        prob_max = prob_range.get("max", prob_max)
        up_min = up_range.get("min", up_min)
        up_max = up_range.get("max", up_max)

    if not prob_min <= success_probability <= prob_max:
        warnings.append(
            f"Probability {success_probability} outside range "
            f"[{prob_min}, {prob_max}]"
        )
    if not up_min <= upside_multiple <= up_max:
        warnings.append(
            f"Upside {upside_multiple} outside range [{up_min}, {up_max}]"
        )
    if downside < 0:
        warnings.append(f"Downside {downside} is negative")
    if downside > upside_multiple * success_probability:
        warnings.append("Downside exceeds expected upside — EV will be negative")

    return len(warnings) == 0, warnings


def determine_tier(ev_adjusted: float, settings: dict) -> str:
    """Map EV to position tier."""
    scaling = settings.get("model", {}).get("ev_scaling", {})
    core_threshold = scaling.get("core", 5.0)
    core_min_threshold = scaling.get("core_min", 4.0)
    secondary_threshold = scaling.get("secondary", 3.0)

    if ev_adjusted >= core_threshold:
        return "core"
    elif ev_adjusted >= core_min_threshold:
        return "core_min"
    elif ev_adjusted >= secondary_threshold:
        return "secondary"
    return "speculative"


def enrich_with_ev(
    df: pd.DataFrame, db_path: str | Path, settings: dict
) -> pd.DataFrame:
    """Add EV columns from database."""
    result = df.copy()
    ev_df = load_all_ev_data(db_path)

    if ev_df.empty:
        for col in ["ev_raw", "ev_adjusted", "tier"]:
            result[col] = None
        return result

    ev_map = ev_df.set_index("ticker")
    for col in ["ev_raw", "ev_adjusted", "tier"]:
        if col in ev_map.columns:
            result[col] = result["ticker"].map(ev_map[col].to_dict())
        else:
            result[col] = None
    return result
