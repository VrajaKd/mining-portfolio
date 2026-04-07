from pathlib import Path

import pandas as pd
import streamlit as st

from dashboards.components import alert_error, alert_info, alert_success, alert_warning
from dashboards.shared import get_db_path, load_and_enrich, rename_for_display
from modules.persistence import SCORE_CRITERIA


def render(settings: dict):
    st.title("Weekly Portfolio Review")

    if "raw_portfolio" not in st.session_state:
        from modules.persistence import load_raw_portfolio

        saved = load_raw_portfolio(get_db_path(settings))
        if not saved.empty:
            st.session_state["raw_portfolio"] = saved
        else:
            alert_info("Load portfolio data on the Daily page first.")
            return

    from modules.ingestion import normalize_holdings

    raw = st.session_state["raw_portfolio"]
    normalized = normalize_holdings(raw)
    enriched = load_and_enrich(normalized, settings)
    total_value = enriched["market_value"].sum()

    # Summary metrics
    scored = enriched["score"].notna()
    col1, col2, col3 = st.columns(3)
    with col1:
        avg_score = enriched.loc[scored, "score"].mean()
        st.metric(
            "Avg Score",
            f"{avg_score:.2f}" if pd.notna(avg_score) else "N/A",
        )
    with col2:
        avg_ev = enriched.loc[scored, "ev_adjusted"].mean()
        st.metric(
            "Avg EV",
            f"{avg_ev:.2f}" if pd.notna(avg_ev) else "N/A",
        )
    with col3:
        sell_threshold = (
            settings.get("model", {})
            .get("risk_thresholds", {})
            .get("sell_candidate", 9)
        )
        high_risk = (enriched["risk_score"] >= sell_threshold).sum()
        st.metric("High Risk", f"{high_risk} / {len(enriched)}")

    # Complete scoring table
    st.subheader("Complete Scoring Table")
    from modules.persistence import load_all_scores

    db_path = get_db_path(settings)
    scores_df = load_all_scores(db_path)

    if not scores_df.empty:
        score_cols = ["ticker", *SCORE_CRITERIA, "final_score"]
        available = [c for c in score_cols if c in scores_df.columns]
        st.dataframe(
            rename_for_display(scores_df[available]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        alert_info("No scores entered yet. Score positions on the Daily page.")

    # Allocation gap table
    st.subheader("Allocation Gap")
    gap_cols = [
        "ticker",
        "score",
        "ev_adjusted",
        "tier",
        "portfolio_weight_pct",
        "target_weight_pct",
        "action",
    ]
    available = [c for c in gap_cols if c in enriched.columns]
    gap_view = enriched[available].copy()

    if "target_weight_pct" in gap_view.columns:
        gap_view["delta_pct"] = (
            gap_view["target_weight_pct"] - gap_view["portfolio_weight_pct"]
        ).round(2)
        gap_view = gap_view.sort_values("delta_pct")

    st.dataframe(
        rename_for_display(gap_view),
        use_container_width=True,
        hide_index=True,
    )

    # Rebalance plan
    st.subheader("Rebalance Plan")
    from modules.rebalance_engine import calculate_rebalance_plan

    plan = calculate_rebalance_plan(enriched, total_value, settings)
    plan_cols = [
        "ticker",
        "rebalance_action",
        "delta_weight_pct",
        "delta_value",
    ]
    available = [c for c in plan_cols if c in plan.columns]
    active = plan[plan["rebalance_action"] != "HOLD"]

    if not active.empty:
        sells = active[active["rebalance_action"] == "TRIM"]
        adds = active[active["rebalance_action"] == "ADD"]

        if not sells.empty:
            st.markdown("**Trim / Sell**")
            st.dataframe(
                rename_for_display(sells[available]),
                use_container_width=True,
                hide_index=True,
            )

        if not adds.empty:
            st.markdown("**Add**")
            st.dataframe(
                rename_for_display(adds[available]),
                use_container_width=True,
                hide_index=True,
            )

        cash_freed = sells["delta_value"].sum() if not sells.empty else 0
        cash_needed = adds["delta_value"].sum() if not adds.empty else 0
        st.metric("Net cash flow", f"${cash_freed + cash_needed:,.2f}")
    else:
        alert_success("Portfolio is balanced — no rebalance actions needed.")

    # Constraint violations
    from modules.rebalance_engine import check_constraints

    violations = check_constraints(enriched, settings)
    if violations:
        st.subheader("Constraint Violations")
        for v in violations:
            if v["severity"] == "high":
                alert_error(v["message"])
            else:
                alert_warning(v["message"])

    # Best ideas
    st.subheader("Best Ideas (Top 5 by EV)")
    if enriched["ev_adjusted"].notna().any():
        top5 = enriched.nlargest(5, "ev_adjusted")
        best_cols = ["ticker", "score", "ev_adjusted", "tier", "action"]
        available = [c for c in best_cols if c in top5.columns]
        st.dataframe(
            rename_for_display(top5[available]),
            use_container_width=True,
            hide_index=True,
        )

    # PDF export
    st.divider()
    from reports.pdf_generator import WeeklyPDFReport

    output = Path(
        settings.get("paths", {}).get("output_reports", "reports")
    )
    output.mkdir(parents=True, exist_ok=True)
    path = WeeklyPDFReport(settings).generate(enriched, output)
    with open(path, "rb") as f:
        st.download_button(
            "Export Weekly PDF", f, file_name=path.name
        )
