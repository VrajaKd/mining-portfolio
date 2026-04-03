from __future__ import annotations

import pandas as pd


def calculate_target_weights(
    df: pd.DataFrame, settings: dict
) -> pd.DataFrame:
    """Assign target weight per position based on EV tier."""
    result = df.copy()
    pos = settings.get("model", {}).get("position_size", {})
    constraints = settings.get("model", {}).get("portfolio_constraints", {})
    max_single = constraints.get("max_single_position", 0.25)

    def _target_weight(row):
        tier = row.get("tier")
        if tier == "core":
            return pos.get("core_max", 0.10)
        elif tier == "core_min":
            return pos.get("core_min", 0.06)
        elif tier == "secondary":
            return (pos.get("secondary_min", 0.03) + pos.get("secondary_max", 0.06)) / 2
        elif tier == "speculative":
            return pos.get("speculative_min", 0.01)
        return 0.0

    result["target_weight_pct"] = result.apply(_target_weight, axis=1) * 100
    max_pct = max_single * 100

    # Iteratively normalize and cap until stable
    for _ in range(5):
        total_target = result["target_weight_pct"].sum()
        if total_target > 0:
            result["target_weight_pct"] = (
                result["target_weight_pct"] / total_target * 100
            )
        result["target_weight_pct"] = result["target_weight_pct"].clip(
            upper=max_pct
        )

    result["target_weight_pct"] = result["target_weight_pct"].round(2)
    return result


def calculate_rebalance_plan(
    df: pd.DataFrame, total_value: float, settings: dict
) -> pd.DataFrame:
    """Calculate trim/add amounts in $ and %."""
    result = df.copy()

    if "target_weight_pct" not in result.columns:
        result = calculate_target_weights(result, settings)

    result["delta_weight_pct"] = (
        result["target_weight_pct"] - result["portfolio_weight_pct"]
    ).round(2)
    result["delta_value"] = (result["delta_weight_pct"] / 100 * total_value).round(2)

    result["rebalance_action"] = result["delta_weight_pct"].apply(
        lambda d: "ADD" if d > 1 else ("TRIM" if d < -1 else "HOLD")
    )

    return result.sort_values("delta_value", ascending=True)


def check_constraints(
    df: pd.DataFrame, settings: dict
) -> list[dict]:
    """Check portfolio constraint violations."""
    violations = []
    constraints = settings.get("model", {}).get("portfolio_constraints", {})
    max_region = constraints.get("max_region_exposure", 0.45) * 100
    max_commodity = constraints.get("max_commodity_exposure", 0.30) * 100
    max_position = constraints.get("max_single_position", 0.25) * 100

    # Single position check
    over_position = df[df["portfolio_weight_pct"] > max_position]
    for _, row in over_position.iterrows():
        violations.append(
            {
                "type": "concentration",
                "message": (
                    f"{row['ticker']}: {row['portfolio_weight_pct']:.1f}% "
                    f"exceeds max {max_position:.0f}%"
                ),
                "severity": "high",
            }
        )

    # Region check
    if "jurisdiction" in df.columns:
        region_exp = df.groupby("jurisdiction")["portfolio_weight_pct"].sum()
        for region, pct in region_exp.items():
            if pct > max_region:
                violations.append(
                    {
                        "type": "region",
                        "message": (
                            f"{region}: {pct:.1f}% exceeds max {max_region:.0f}%"
                        ),
                        "severity": "medium",
                    }
                )

    # Commodity check
    if "commodity" in df.columns:
        comm_exp = df.groupby("commodity")["portfolio_weight_pct"].sum()
        for comm, pct in comm_exp.items():
            if pct > max_commodity:
                violations.append(
                    {
                        "type": "commodity",
                        "message": (
                            f"{comm}: {pct:.1f}% exceeds max {max_commodity:.0f}%"
                        ),
                        "severity": "medium",
                    }
                )

    return violations
