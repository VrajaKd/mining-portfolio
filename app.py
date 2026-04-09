from pathlib import Path

import streamlit as st
import yaml


def load_settings() -> dict:
    config_path = Path("config/settings.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def _render_settings(settings: dict):
    st.title("Settings")

    st.subheader("Data Management")
    st.markdown(
        "Clear all saved data — scores, EV inputs, "
        "and cached portfolio. This cannot be undone."
    )
    if st.button("Clear all data", type="primary"):
        st.session_state["_confirm_clear"] = True

    if st.session_state.get("_confirm_clear"):
        st.warning("Are you sure? This will delete all scores, EV inputs, and cached portfolio data.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, clear everything", type="primary"):
                from modules.persistence import clear_all_data

                db_path = settings.get("paths", {}).get(
                    "database", "data/processed/scoring_data.db"
                )
                clear_all_data(db_path)
                for key in list(st.session_state.keys()):
                    if key not in ("nav_page", "_data_cleared"):
                        del st.session_state[key]
                st.session_state["_data_cleared"] = True
                st.rerun()
        with col2:
            if st.button("Cancel"):
                del st.session_state["_confirm_clear"]
                st.rerun()

    if st.session_state.pop("_data_cleared", False):
        from dashboards.components import alert_success

        alert_success("All data cleared successfully.")


def main():
    st.set_page_config(
        page_title="Portfolio Intelligence V7",
        page_icon="⛏️",
        layout="wide",
    )

    settings = load_settings()

    # Custom styles
    st.markdown("""
    <style>
        section[data-testid="stSidebar"] {
            background-color: #355070;
            width: 200px !important;
            min-width: 200px !important;
        }
        /* Push Settings to sidebar bottom */
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            display: flex !important;
            flex-direction: column !important;
            min-height: calc(100vh - 80px) !important;
        }
        section[data-testid="stSidebar"]
        [data-testid="stVerticalBlock"] > div:last-child {
            margin-top: auto !important;
        }
        /* Center content with max width */
        section[data-testid="stMain"] > div {
            max-width: 1100px;
            margin: 0 auto;
        }
        /* Sidebar nav buttons — look like text links */
        section[data-testid="stSidebar"] button,
        section[data-testid="stSidebar"] button p,
        section[data-testid="stSidebar"] button span,
        section[data-testid="stSidebar"] button div {
            background: none !important;
            border: none !important;
            box-shadow: none !important;
            color: rgba(255,255,255,0.7) !important;
            font-size: 18px !important;
            font-weight: 400 !important;
            justify-content: flex-start !important;
        }
        section[data-testid="stSidebar"] button:hover,
        section[data-testid="stSidebar"] button:hover p,
        section[data-testid="stSidebar"] button:hover span {
            color: white !important;
            background: none !important;
        }
        section[data-testid="stSidebar"] button[kind="primary"],
        section[data-testid="stSidebar"] button[kind="primary"] p,
        section[data-testid="stSidebar"] button[kind="primary"] span {
            color: #eaac8b !important;
            font-weight: 600 !important;
            background: none !important;
        }
        /* Main content primary buttons */
        section[data-testid="stMain"] button[kind="primary"] {
            background-color: #355070 !important;
            border-color: #355070 !important;
            color: white !important;
        }
        section[data-testid="stMain"] button[kind="primary"]:hover {
            background-color: #4a6a8a !important;
            border-color: #4a6a8a !important;
        }
        /* Secondary buttons (Export etc) */
        section[data-testid="stMain"] button[kind="secondary"] {
            background-color: #eaac8b !important;
            border-color: #eaac8b !important;
            color: white !important;
        }
        section[data-testid="stMain"] button[kind="secondary"]:hover {
            background-color: #d4956f !important;
            border-color: #d4956f !important;
        }
        div[data-testid="stMetricLabel"] {
            color: #6d597a !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Navigation via session state
    pages = ["Daily", "Weekly", "Monthly"]
    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "Daily"

    with st.sidebar:
        for p in pages:
            is_active = p == st.session_state["nav_page"]
            st.button(
                p,
                key=f"nav_{p}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
                on_click=lambda sel=p: st.session_state.update(
                    nav_page=sel
                ),
            )

        # Settings — separated from main nav
        st.divider()
        is_settings = st.session_state["nav_page"] == "Settings"
        st.button(
            "Settings",
            key="nav_Settings",
            use_container_width=True,
            type="primary" if is_settings else "secondary",
            on_click=lambda: st.session_state.update(
                nav_page="Settings"
            ),
        )

    page = st.session_state["nav_page"]

    if page == "Daily":
        from dashboards.daily import render

        render(settings)
    elif page == "Weekly":
        from dashboards.weekly import render

        render(settings)
    elif page == "Monthly":
        from dashboards.monthly import render

        render(settings)
    elif page == "Settings":
        _render_settings(settings)


if __name__ == "__main__":
    main()
