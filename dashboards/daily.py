import os
from pathlib import Path

import pandas as pd
import streamlit as st

from dashboards.components import alert_error, alert_info, alert_success, alert_warning
from dashboards.shared import (
    get_db_path,
    load_and_enrich,
    rename_for_display,
)


def _render_scoring_input(
    tickers: list[str],
    settings: dict,
    preselected: str | None = None,
):
    from modules.ev_engine import calculate_ev, determine_tier
    from modules.persistence import (
        SCORE_CRITERIA,
        init_database,
        load_ev_data,
        load_scores,
        save_ev_data,
        save_scores,
    )
    from modules.scoring import (
        calculate_weighted_score,
        get_scoring_rubric,
        load_rubrics,
    )

    db_path = get_db_path(settings)
    init_database(db_path)
    weights = settings.get("model", {}).get("score_weights", {})

    rubrics_path = settings.get("rubrics_file", "config/scoring_rubrics.yaml")
    rubrics = load_rubrics(rubrics_path)

    st.subheader(f"Score: {preselected}")

    selected = preselected
    if not selected:
        return

    existing_scores = load_scores(db_path, selected) or {}
    existing_ev = load_ev_data(db_path, selected) or {}

    st.markdown("**Criteria scores (0-10)**")
    raw_scores = {}
    for criterion in SCORE_CRITERIA:
        name = rubrics.get(criterion, {}).get("name", criterion)
        weight = weights.get(criterion, 0.0)
        default = existing_scores.get(criterion, 5.0) or 5.0
        val = st.slider(
            f"{name} ({weight:.0%})",
            min_value=0.0,
            max_value=10.0,
            value=float(default),
            step=0.5,
            key=f"score_{selected}_{criterion}",
        )
        raw_scores[criterion] = val
        hint = get_scoring_rubric(rubrics, criterion, val)
        if hint:
            st.caption(hint)

    preview_score = calculate_weighted_score(raw_scores, weights)
    st.metric("Estimated Score", f"{preview_score:.2f}")

    st.markdown("**EV inputs**")
    ev_model = settings.get("model", {}).get("ev_model", {})
    up_range = ev_model.get("upside_range", {})
    prob_range = ev_model.get("probability_range", {})

    upside = st.number_input(
        "Upside multiple",
        min_value=float(up_range.get("min", 5)),
        max_value=float(up_range.get("max", 50)),
        value=float(existing_ev.get("upside_multiple", 10.0) or 10.0),
        step=1.0,
        key=f"ev_upside_{selected}",
    )
    probability = st.number_input(
        "Success probability",
        min_value=float(prob_range.get("min", 0.25)),
        max_value=float(prob_range.get("max", 0.80)),
        value=float(existing_ev.get("success_probability", 0.50) or 0.50),
        step=0.05,
        key=f"ev_prob_{selected}",
    )
    downside = st.number_input(
        "Downside",
        min_value=0.0,
        max_value=10.0,
        value=float(existing_ev.get("downside", 1.0) or 1.0),
        step=0.5,
        key=f"ev_down_{selected}",
    )
    catalyst_labels = {
        "Near term (×1.2)": "near_term",
        "Mid term (×1.0)": "mid_term",
        "Long term (×0.8)": "long_term",
    }
    label_list = list(catalyst_labels.keys())
    value_list = list(catalyst_labels.values())
    current_value = existing_ev.get("catalyst_timing", "mid_term") or "mid_term"
    catalyst_label = st.selectbox(
        "Catalyst timing",
        label_list,
        index=value_list.index(current_value),
        key=f"ev_catalyst_{selected}",
    )
    catalyst_timing = catalyst_labels[catalyst_label]

    ev_result = calculate_ev(
        upside, probability, downside, catalyst_timing, settings
    )
    tier = determine_tier(ev_result["ev_adjusted"], settings)

    tier_labels = {
        "core": "Core",
        "core_min": "Core (min)",
        "secondary": "Secondary",
        "speculative": "Speculative",
    }

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Expected Value", f"{ev_result['ev_adjusted']:.2f}")
    with col2:
        st.metric("Tier", tier_labels.get(tier, tier))
    with col3:
        st.metric(
            "Catalyst multiplier",
            f"×{ev_result['catalyst_multiplier']:.1f}",
        )

    col_save, col_top = st.columns([1, 1])
    with col_save:
        if st.button("Save Scores", type="primary"):
            raw_scores["final_score"] = preview_score
            save_scores(db_path, selected, raw_scores)
            ev_result["tier"] = tier
            save_ev_data(db_path, selected, ev_result)
            alert_success(f"Saved scores for {selected}")
            st.rerun()
    with col_top:
        st.markdown(
            "<style>"
            ".back-top a { color: #6d597a; text-decoration: none; }"
            ".back-top a:hover { color: #9b85a6; }"
            "</style>"
            '<div class="back-top" style="text-align: right;">'
            '<a href="#daily-portfolio-overview">↑ Back to top</a>'
            "</div>",
            unsafe_allow_html=True,
        )


def _render_decision_table(enriched: pd.DataFrame):
    st.subheader("Decision Dashboard")

    display_cols = [
        "ticker",
        "score",
        "ev_adjusted",
        "risk_score",
        "action",
        "portfolio_weight_pct",
        "target_weight_pct",
    ]
    available = [c for c in display_cols if c in enriched.columns]
    view = enriched[available].copy()
    view = rename_for_display(view)

    def _color_action(val):
        action_colors = {
            "BUY": "background-color: #6b8f71; color: white",
            "ADD": "background-color: #355070; color: white",
            "HOLD": "background-color: #eaac8b; color: #355070",
            "SELL": "background-color: #e56b6f; color: white",
            "No Score": "background-color: #f5e6d8; color: #355070",
        }
        return action_colors.get(val, "")

    action_col = "Action"
    if action_col in view.columns:
        styled = view.style.map(
            _color_action, subset=[action_col]
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.dataframe(view, use_container_width=True, hide_index=True)


def _render_risk_flags(enriched: pd.DataFrame, settings: dict):
    threshold = (
        settings.get("model", {})
        .get("risk_thresholds", {})
        .get("sell_candidate", 9)
    )
    high_risk = enriched[enriched["risk_score"] >= threshold]
    if high_risk.empty:
        return

    st.subheader("Risk Flags")
    for _, row in high_risk.iterrows():
        alert_error(
            f"<b>{row['ticker']}</b> — Risk {row['risk_score']} "
            f"| Action: {row.get('action', 'N/A')}"
        )


def _render_swap_candidates(enriched: pd.DataFrame, settings: dict):
    from modules.decision_engine import find_swap_candidates

    swaps = find_swap_candidates(enriched, settings)
    if swaps.empty:
        return

    st.subheader("Swap Candidates")
    st.dataframe(rename_for_display(swaps), use_container_width=True, hide_index=True)


def render(settings: dict):
    st.title("Daily Portfolio Overview")

    ib_available = bool(os.environ.get("IBKR_HOST"))
    sources = ["IB API", "CSV Upload"] if ib_available else ["CSV Upload"]
    source = st.radio("Data source", sources, horizontal=True)

    from modules.persistence import (
        init_database,
        load_raw_portfolio,
        save_raw_portfolio,
    )

    db_path = get_db_path(settings)
    init_database(db_path)

    df = pd.DataFrame()

    if source == "IB API":
        if st.button("Load from IB"):
            with st.spinner("Connecting to IB..."):
                try:
                    from modules.ingestion import connect_ib, fetch_portfolio

                    ib = connect_ib()
                    raw = fetch_portfolio(ib)
                    ib.disconnect()
                    st.session_state["raw_portfolio"] = raw
                    save_raw_portfolio(db_path, raw)
                except Exception as e:
                    alert_error(f"IB connection failed: {e}")
                    return

    else:
        uploaded = st.file_uploader("Upload IB CSV export", type=["csv"])
        if uploaded is not None:
            try:
                from modules.ingestion import parse_ib_csv

                df = parse_ib_csv(uploaded)
                st.session_state["raw_portfolio"] = df
                save_raw_portfolio(db_path, df)
            except (ValueError, Exception) as e:
                alert_error(f"CSV parse error: {e}")
                return

    # Restore from session or database
    if df.empty and "raw_portfolio" in st.session_state:
        df = st.session_state["raw_portfolio"]
    if df.empty:
        saved = load_raw_portfolio(db_path)
        if not saved.empty:
            st.session_state["raw_portfolio"] = saved
            df = saved

    if df.empty:
        alert_info("Load portfolio data to begin.")
        return

    from modules.ingestion import normalize_holdings, validate_holdings

    normalized = normalize_holdings(df)
    normalized, warnings = validate_holdings(normalized)

    if warnings:
        for w in warnings:
            alert_warning(w)

    # Summary metrics
    col1, col2 = st.columns(2)
    with col1:
        total_value = normalized["market_value"].sum()
        st.metric("Total Portfolio Value", f"${total_value:,.2f}")
    with col2:
        st.metric("Positions", len(normalized))

    # Enrich with scoring data
    enriched = load_and_enrich(normalized, settings)

    # Decision table
    _render_decision_table(enriched)

    # Ticker selection — visually connected to table
    tickers = enriched["ticker"].tolist()
    selected = st.pills(
        "Score a position — select ticker",
        tickers,
        label_visibility="collapsed",
    )

    if selected:
        _render_scoring_input(tickers, settings, selected)

    # Risk flags
    _render_risk_flags(enriched, settings)

    # Swap candidates
    _render_swap_candidates(enriched, settings)

    # PDF export
    st.divider()
    from reports.pdf_generator import DailyPDFReport

    output = Path(
        settings.get("paths", {}).get("output_reports", "reports")
    )
    output.mkdir(parents=True, exist_ok=True)
    path = DailyPDFReport(settings).generate(enriched, output)
    col_pdf, col_top = st.columns([1, 1])
    with col_pdf:
        with open(path, "rb") as f:
            st.download_button(
                "Export Daily PDF", f, file_name=path.name
            )
    with col_top:
        st.markdown(
            "<style>"
            ".back-top a { color: #6d597a; text-decoration: none; }"
            ".back-top a:hover { color: #9b85a6; }"
            "</style>"
            '<div class="back-top" style="text-align: right;">'
            '<a href="#daily-portfolio-overview">↑ Back to top</a>'
            "</div>",
            unsafe_allow_html=True,
        )
