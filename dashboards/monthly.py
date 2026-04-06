from pathlib import Path

import streamlit as st

from dashboards.components import alert_info
from dashboards.shared import load_and_enrich, rename_for_display


def render(settings: dict):
    st.title("Monthly Strategic Review")

    if "raw_portfolio" not in st.session_state:
        alert_info("Load portfolio data on the Daily page first.")
        return

    from modules.ingestion import normalize_holdings

    raw = st.session_state["raw_portfolio"]
    normalized = normalize_holdings(raw)
    enriched = load_and_enrich(normalized, settings)
    total_value = enriched["market_value"].sum()

    # Performance summary
    st.subheader("Portfolio Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Value", f"${total_value:,.2f}")
    with col2:
        has_pl = (
            "unrealized_pl" in enriched.columns
            and not enriched["unrealized_pl"].isna().all()
        )
        best = enriched.loc[enriched["unrealized_pl"].idxmax()] if has_pl else None
        if best is not None:
            best_pl = best["unrealized_pl"]
            st.metric(
                "Best Position",
                best["ticker"],
                delta=round(best_pl, 2),
                delta_color="normal",
            )
        else:
            st.metric("Best Position", "N/A")
    with col3:
        worst = enriched.loc[enriched["unrealized_pl"].idxmin()] if has_pl else None
        if worst is not None:
            worst_pl = worst["unrealized_pl"]
            st.metric(
                "Worst Position",
                worst["ticker"],
                delta=round(worst_pl, 2),
                delta_color="normal",
            )
        else:
            st.metric("Worst Position", "N/A")

    # Sector exposure — commodity
    st.subheader("Commodity Exposure")
    if "commodity" in enriched.columns:
        comm = enriched.groupby("commodity").agg(
            weight=("portfolio_weight_pct", "sum"),
            positions=("ticker", "count"),
        ).sort_values("weight", ascending=False)
        max_commodity = (
            settings.get("model", {})
            .get("portfolio_constraints", {})
            .get("max_commodity_exposure", 0.30)
            * 100
        )
        comm["target_max"] = max_commodity
        comm["status"] = comm["weight"].apply(
            lambda w: "OVERWEIGHT" if w > max_commodity else "OK"
        )
        st.dataframe(comm, use_container_width=True)
    else:
        alert_info(
            "Commodity data not available. "
            "Add commodity field to portfolio data."
        )

    # Sector exposure — region
    st.subheader("Region Exposure")
    if "jurisdiction" in enriched.columns:
        region = enriched.groupby("jurisdiction").agg(
            weight=("portfolio_weight_pct", "sum"),
            positions=("ticker", "count"),
        ).sort_values("weight", ascending=False)
        max_region = (
            settings.get("model", {})
            .get("portfolio_constraints", {})
            .get("max_region_exposure", 0.45)
            * 100
        )
        region["target_max"] = max_region
        region["status"] = region["weight"].apply(
            lambda w: "OVERWEIGHT" if w > max_region else "OK"
        )
        st.dataframe(region, use_container_width=True)
    else:
        alert_info(
            "Region data not available. "
            "Add jurisdiction field to portfolio data."
        )

    # Strategic positioning
    st.subheader("Strategic Positioning")
    if "tier" in enriched.columns and enriched["tier"].notna().any():
        tiers = enriched.groupby("tier").agg(
            positions=("ticker", "count"),
            weight=("portfolio_weight_pct", "sum"),
            avg_score=("score", "mean"),
            avg_ev=("ev_adjusted", "mean"),
        ).round(2)
        st.dataframe(tiers, use_container_width=True)
    else:
        alert_info("Score positions on the Daily page to see tier breakdown.")

    # Full portfolio table
    st.subheader("Full Portfolio")
    display_cols = [
        "ticker",
        "quantity",
        "market_value",
        "portfolio_weight_pct",
        "score",
        "ev_adjusted",
        "risk_score",
        "tier",
        "action",
    ]
    available = [c for c in display_cols if c in enriched.columns]
    st.dataframe(
        rename_for_display(
            enriched[available].sort_values("portfolio_weight_pct", ascending=False)
        ),
        use_container_width=True,
        hide_index=True,
    )

    # PDF export
    st.divider()
    from reports.pdf_generator import MonthlyPDFReport

    output = Path(
        settings.get("paths", {}).get("output_reports", "reports")
    )
    output.mkdir(parents=True, exist_ok=True)
    path = MonthlyPDFReport(settings).generate(enriched, output)
    with open(path, "rb") as f:
        st.download_button(
            "Export Monthly PDF", f, file_name=path.name
        )
