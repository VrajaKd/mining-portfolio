from pathlib import Path

import pandas as pd
import streamlit as st


def _get_db_path(settings: dict) -> str:
    return settings.get("paths", {}).get(
        "database", "data/processed/scoring_data.db"
    )


def _load_and_enrich(normalized: pd.DataFrame, settings: dict) -> pd.DataFrame:
    from modules.decision_engine import enrich_with_decisions
    from modules.ev_engine import enrich_with_ev
    from modules.persistence import init_database
    from modules.rebalance_engine import calculate_target_weights
    from modules.risk_engine import enrich_with_risk
    from modules.scoring import enrich_with_scores

    db_path = _get_db_path(settings)
    init_database(db_path)

    df = enrich_with_scores(normalized, db_path)
    df = enrich_with_ev(df, db_path, settings)
    df = enrich_with_risk(df, settings)
    df = enrich_with_decisions(df, settings)
    df = calculate_target_weights(df, settings)
    return df


def _render_scoring_input(
    tickers: list[str], settings: dict
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

    db_path = _get_db_path(settings)
    init_database(db_path)
    weights = settings.get("model", {}).get("score_weights", {})

    rubrics_path = settings.get("rubrics_file", "config/scoring_rubrics.yaml")
    rubrics = load_rubrics(rubrics_path)

    st.subheader("Score Input")

    selected = st.selectbox("Select ticker", tickers)
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
            key=f"score_{criterion}",
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
    )
    probability = st.number_input(
        "Success probability",
        min_value=float(prob_range.get("min", 0.25)),
        max_value=float(prob_range.get("max", 0.80)),
        value=float(existing_ev.get("success_probability", 0.50) or 0.50),
        step=0.05,
    )
    downside = st.number_input(
        "Downside",
        min_value=0.0,
        max_value=10.0,
        value=float(existing_ev.get("downside", 1.0) or 1.0),
        step=0.5,
    )
    catalyst_timing = st.selectbox(
        "Catalyst timing",
        ["near_term", "mid_term", "long_term"],
        index=["near_term", "mid_term", "long_term"].index(
            existing_ev.get("catalyst_timing", "mid_term") or "mid_term"
        ),
    )

    ev_result = calculate_ev(
        upside, probability, downside, catalyst_timing, settings
    )
    tier = determine_tier(ev_result["ev_adjusted"], settings)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("EV (adjusted)", f"{ev_result['ev_adjusted']:.2f}")
    with col2:
        st.metric("Tier", tier.upper())
    with col3:
        st.metric(
            "Catalyst",
            f"×{ev_result['catalyst_multiplier']:.1f}",
        )

    if st.button("Save Scores", type="primary"):
        raw_scores["final_score"] = preview_score
        save_scores(db_path, selected, raw_scores)
        ev_result["tier"] = tier
        save_ev_data(db_path, selected, ev_result)
        st.success(f"Saved scores for {selected}")
        st.rerun()


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

    def _color_action(val):
        colors = {
            "BUY": "background-color: #c6efce",
            "ADD": "background-color: #c6efce",
            "HOLD": "",
            "SELL": "background-color: #ffc7ce",
            "NO_DATA": "background-color: #ffeb9c",
        }
        return colors.get(val, "")

    if "action" in view.columns:
        styled = view.style.map(_color_action, subset=["action"])
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
        st.error(
            f"**{row['ticker']}** — Risk {row['risk_score']} "
            f"| Action: {row.get('action', 'N/A')}"
        )


def _render_swap_candidates(enriched: pd.DataFrame, settings: dict):
    from modules.decision_engine import find_swap_candidates

    swaps = find_swap_candidates(enriched, settings)
    if swaps.empty:
        return

    st.subheader("Swap Candidates")
    st.dataframe(swaps, use_container_width=True, hide_index=True)


def render(settings: dict):
    st.title("Daily Portfolio Overview")

    source = st.radio("Data source", ["IB API", "CSV Upload"], horizontal=True)

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
                except Exception as e:
                    st.error(f"IB connection failed: {e}")
                    return

        if "raw_portfolio" in st.session_state:
            df = st.session_state["raw_portfolio"]

    else:
        uploaded = st.file_uploader("Upload IB CSV export", type=["csv"])
        if uploaded is not None:
            try:
                from modules.ingestion import parse_ib_csv

                df = parse_ib_csv(uploaded)
            except (ValueError, Exception) as e:
                st.error(f"CSV parse error: {e}")
                return

    if df.empty:
        st.info("Load portfolio data to begin.")
        return

    from modules.ingestion import normalize_holdings, validate_holdings

    normalized = normalize_holdings(df)
    normalized, warnings = validate_holdings(normalized)

    if warnings:
        for w in warnings:
            st.warning(w)

    # Summary metrics
    col1, col2 = st.columns(2)
    with col1:
        total_value = normalized["market_value"].sum()
        st.metric("Total Portfolio Value", f"${total_value:,.2f}")
    with col2:
        st.metric("Positions", len(normalized))

    # Enrich with scoring data
    enriched = _load_and_enrich(normalized, settings)

    # Decision table
    _render_decision_table(enriched)

    # Risk flags
    _render_risk_flags(enriched, settings)

    # Swap candidates
    _render_swap_candidates(enriched, settings)

    # Scoring input (collapsible)
    with st.expander("Score a position", expanded=False):
        _render_scoring_input(
            enriched["ticker"].tolist(), settings
        )

    # PDF export
    st.divider()
    if st.button("Export Daily PDF"):
        from reports.pdf_generator import DailyPDFReport

        output = Path(
            settings.get("paths", {}).get("output_reports", "reports")
        )
        output.mkdir(parents=True, exist_ok=True)
        path = DailyPDFReport(settings).generate(enriched, output)
        with open(path, "rb") as f:
            st.download_button("Download PDF", f, file_name=path.name)
