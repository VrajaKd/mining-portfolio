import pandas as pd
import streamlit as st


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

    display_cols = [
        "ticker",
        "company_name",
        "quantity",
        "market_value",
        "avg_cost",
        "unrealized_pl",
        "portfolio_weight_pct",
    ]
    available = [c for c in display_cols if c in normalized.columns]

    st.subheader(f"Portfolio ({len(normalized)} positions)")
    st.dataframe(
        normalized[available],
        use_container_width=True,
        hide_index=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        total_value = normalized["market_value"].sum()
        st.metric("Total Portfolio Value", f"${total_value:,.2f}")
    with col2:
        st.metric("Positions", len(normalized))
