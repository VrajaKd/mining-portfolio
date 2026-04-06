from pathlib import Path

import streamlit as st
import yaml


def load_settings() -> dict:
    config_path = Path("config/settings.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


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


if __name__ == "__main__":
    main()
